from flask import Blueprint, request, g
from .models import Product, Order, OrderItem, PaymentStatus, ShippingStatus
from . import db
import random, string
from app.utils.response import UnifiedResponse
from app.utils.pagination import UnifiedPagination
from app.utils.decorators import auth_required, role_required


STAFF_ROLES = {'admin', 'moderator'}


def _is_staff(user) -> bool:
    """Admin or moderator — anyone with elevated privileges."""
    return bool(user and user.role and user.role.name in STAFF_ROLES)


def _can_access_order(user, order) -> bool:
    """An order is accessible to its owner and to staff (admin/moderator)."""
    if _is_staff(user):
        return True
    return order.user_id == user.id

# api for order process:
# Endpoints
#   - POST api/orders
#     in: [{product_id:int, quantity: int}]
#     out: order details or failure with message
#   - POST api/orders/{order-id}/pay
#     out: order details (with updated fields:reference)

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/orders', methods=['GET'])
@auth_required
def get_orders():
    """
    List orders with pagination. Admins see all orders; regular users see only their own.

    Query params:
        - page / page_size  (page-based pagination)
        - limit / offset    (limit/offset pagination)
        - pagination_type: 'page' or 'limit_offset' (default: 'page')
    """
    user = g.current_user

    queryset = Order.query
    if not _is_staff(user):
        queryset = queryset.filter(Order.user_id == user.id)
    queryset = queryset.order_by(Order.id.desc())

    # Determine pagination type
    pagination_type = request.args.get('pagination_type', 'page')

    if pagination_type == 'limit_offset':
        return UnifiedPagination.paginate_by_limit_offset(
            queryset=queryset,
            serializer_func=lambda order: order.serialize(),
            message="Orders retrieved successfully"
        )
    else:
        return UnifiedPagination.paginate_by_page(
            queryset=queryset,
            serializer_func=lambda order: order.serialize(),
            message="Orders retrieved successfully")

@bp.route('/products', methods=['GET'])
def list_products():
    """
    Public: list products with pagination.

    Query params:
        - page / page_size  (page-based pagination)
        - limit / offset    (limit/offset pagination)
        - pagination_type: 'page' or 'limit_offset' (default: 'page')
    """
    queryset = Product.query.order_by(Product.id.asc())
    pagination_type = request.args.get('pagination_type', 'page')

    if pagination_type == 'limit_offset':
        return UnifiedPagination.paginate_by_limit_offset(
            queryset=queryset,
            serializer_func=lambda prod: prod.serialize(),
            message="Products retrieved successfully"
        )
    return UnifiedPagination.paginate_by_page(
        queryset=queryset,
        serializer_func=lambda prod: prod.serialize(),
        message="Products retrieved successfully"
    )


@bp.route('/products', methods=['POST'])
@auth_required
@role_required(['admin', 'moderator'])
def create_product():
    """Staff-only (admin/moderator): create a new product."""
    if not request.is_json:
        return UnifiedResponse.error(
            message="Request body should be in JSON format",
            status_code=400
        )

    body = request.get_json()

    required_fields = ['name', 'price', 'stock']
    missing_fields = [field for field in required_fields if field not in body]

    if missing_fields:
        return UnifiedResponse.validation_error({
            'missing_fields': missing_fields,
            'message': f'Required fields: {", ".join(required_fields)}'
        })

    try:
        product = Product(
            name=body['name'],
            price=body['price'],
            stock=body['stock']
        )
        db.session.add(product)
        db.session.commit()

        return UnifiedResponse.created(
            data=product.serialize(),
            message="Product created successfully",
            resource_id=product.id
        )
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to create product: {str(e)}',
            status_code=500
        )


# for orders

@bp.route('/orders', methods=['POST'])
@auth_required
def create_order():
    """
    Create a new order.
    Requires authentication.
    """
    user = g.current_user

    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400
        )

    body = request.get_json()

    # name/email default to the authenticated user's profile when not provided.
    full_name = (
        f"{user.first_name} {user.last_name}".strip()
        if (user.first_name or user.last_name) else user.username
    )
    name = body.get('name') or full_name
    email = body.get('email') or user.email

    if 'items' not in body:
        return UnifiedResponse.validation_error({
            'missing_fields': ['items'],
            'message': 'Required field: items'
        })

    if not isinstance(body['items'], list) or len(body['items']) == 0:
        return UnifiedResponse.validation_error({
            'items': 'items must be a non-empty list'
        })

    # apply atomicity for transaction -> all or none
    try:
        order = Order(
            name=name,
            email=email,
            user_id=user.id,
            payment_status=PaymentStatus.PENDING,
            shipping_status=ShippingStatus.PENDING
        )
        db.session.add(order)
        db.session.flush()

        for item in body['items']:
            if not all(k in item for k in ['product_id', 'quantity']):
                return UnifiedResponse.validation_error({
                    'items': 'Each item must have product_id and quantity'
                })

            product = db.session.get(Product, item['product_id'])
            if not product:
                return UnifiedResponse.not_found(
                    message=f'Product with ID {item["product_id"]} not found'
                )

            if product.stock < item['quantity']:
                return UnifiedResponse.error(
                    message=f'Insufficient stock for product {product.name}. Available: {product.stock}',
                    error_code='INSUFFICIENT_STOCK',
                    status_code=400
                )

            order_item = OrderItem(
                order_id=order.id,
                product_id=item['product_id'],
                quantity=item['quantity']
            )

            product.stock -= item['quantity']
            db.session.add(order_item)

        db.session.commit()

        return UnifiedResponse.created(
            data=order.serialize(),
            message="Order created successfully",
            resource_id=order.id
        )

    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to create order: {str(e)}',
            status_code=500
        )


# for an existing order -> to add more items
@bp.route('/orders/<int:order_id>/items', methods=['POST'])
@auth_required
def add_more_items(order_id):
    """
    Add items to an existing order.
    Requires authentication and ownership (or admin).
    """
    order = db.session.get(Order, order_id)
    if not order:
        return UnifiedResponse.not_found(
            message=f"Order with ID {order_id} not found"
        )

    if not _can_access_order(g.current_user, order):
        return UnifiedResponse.forbidden(
            message="You do not have access to this order"
        )

    if order.payment_status == PaymentStatus.PAID:
        return UnifiedResponse.error(
            message='Cannot add items to a paid order. Please create a new order.',
            error_code='ORDER_ALREADY_PAID',
            status_code=400
        )

    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400
        )

    data = request.get_json()

    # Validate required fields
    if not all(k in data for k in ['product_id', 'quantity']):
        return UnifiedResponse.validation_error({
            'message': 'Missing required fields: product_id, quantity'
        })

    product = db.session.get(Product, data['product_id'])
    if not product:
        return UnifiedResponse.not_found(
            message=f"Product with ID {data['product_id']} not found"
        )

    if product.stock < data['quantity']:
        return UnifiedResponse.error(
            message=f'Insufficient stock. Available: {product.stock}, Requested: {data["quantity"]}',
            error_code='INSUFFICIENT_STOCK',
            status_code=400
        )

    try:
        order_item = OrderItem(
            order_id=order_id,
            product_id=data['product_id'],
            quantity=data['quantity']
        )

        product.stock -= data['quantity']

        db.session.add(order_item)
        db.session.commit()

        return UnifiedResponse.created(
            data=order_item.serialize(),
            message="Item added to order successfully",
            resource_id=order_item.id
        )
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to add item to order: {str(e)}',
            status_code=500
        )


@bp.route('/orders/<int:order_id>/pay', methods=['POST'])
@auth_required
def pay_order(order_id):
    """
    Process payment for an order.
    Requires authentication and ownership (or admin).
    """
    order = db.session.get(Order, order_id)
    if not order:
        return UnifiedResponse.not_found(
            message=f"Order with ID {order_id} not found"
        )

    if not _can_access_order(g.current_user, order):
        return UnifiedResponse.forbidden(
            message="You do not have access to this order"
        )

    if order.payment_status == PaymentStatus.PAID:
        return UnifiedResponse.error(
            message='Order already paid',
            error_code='ORDER_ALREADY_PAID',
            status_code=400
        )

    if len(order.items) == 0:
        return UnifiedResponse.error(
            message='Cannot pay for an order with no items',
            error_code='EMPTY_ORDER',
            status_code=400
        )

    try:
        payment_reference = 'Ref_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        order.payment_status = PaymentStatus.PAID
        order.payment_reference = payment_reference

        db.session.commit()

        # Import here to avoid circular imports
        from app.tasks import send_order_confirmation
        send_order_confirmation.delay(order.id)

        return UnifiedResponse.success(
            data={
                'payment_reference': payment_reference,
                'order': order.serialize()
            },
            message='Payment successful'
        )
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Payment failed: {str(e)}',
            status_code=400
        )


@bp.route('/orders/<int:order_id>/status', methods=['PATCH'])
@auth_required
def update_shipping_status(order_id):
    """
    Admin-only: update an order's shipping_status.

    Body: {"shipping_status": "pending" | "in_progress" | "delivered"}

    DB write is synchronous (so we can return the fresh order); the email
    notification is fired off to Celery.
    """
    if not _is_staff(g.current_user):
        return UnifiedResponse.forbidden(
            message="Only staff can update shipping status"
        )

    order = db.session.get(Order, order_id)
    if not order:
        return UnifiedResponse.not_found(
            message=f"Order with ID {order_id} not found"
        )

    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400,
        )

    new_status = (request.get_json() or {}).get('shipping_status')
    if not new_status:
        return UnifiedResponse.validation_error({
            'shipping_status': 'shipping_status is required',
        })

    try:
        status_enum = ShippingStatus(new_status)
    except ValueError:
        return UnifiedResponse.validation_error({
            'shipping_status': f"Must be one of: {', '.join(s.value for s in ShippingStatus)}",
        })

    if order.shipping_status == status_enum:
        # No-op — don't queue a redundant email.
        return UnifiedResponse.success(
            data=order.serialize(),
            message="Shipping status unchanged",
        )

    try:
        order.shipping_status = status_enum
        db.session.commit()

        from app.tasks import notify_shipping_status
        notify_shipping_status.delay(order.id)

        return UnifiedResponse.success(
            data=order.serialize(),
            message=f"Shipping status updated to {status_enum.value}",
        )
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f"Failed to update shipping status: {str(e)}",
            status_code=500,
        )


@bp.route('/orders/<int:order_id>', methods=['GET'])
@auth_required
def get_order(order_id):
    """
    Get a specific order by ID. Owner or admin only.
    """
    order = db.session.get(Order, order_id)
    if not order:
        return UnifiedResponse.not_found(
            message=f"Order with ID {order_id} not found"
        )

    if not _can_access_order(g.current_user, order):
        return UnifiedResponse.forbidden(
            message="You do not have access to this order"
        )

    return UnifiedResponse.success(
        data=order.serialize(),
        message="Order retrieved successfully"
    )
