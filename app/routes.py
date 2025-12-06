from flask import Blueprint, request, g
from .models import Product, Order, OrderItem, PaymentStatus, ShippingStatus
from . import db
import random, string
from app.utils.response import UnifiedResponse
from app.utils.pagination import UnifiedPagination
from app.utils.decorators import auth_required, role_required, optional_auth

# api for order process:
# Endpoints
#   - POST api/orders
#     in: [{product_id:int, quantity: int}]
#     out: order details or failure with message
#   - POST api/orders/{order-id}/pay
#     out: order details (with updated fields:reference)

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/orders', methods=['GET'])
@optional_auth
def get_orders():
    """
    Get all orders with pagination.
    If authenticated, filter by user (future feature).

    Query params:
        - page: Page number (for page-based pagination)
        - page_size: Items per page (for page-based pagination)
        - limit: Number of items (for limit/offset pagination)
        - offset: Starting position (for limit/offset pagination)
        - pagination_type: 'page' or 'limit_offset' (default: 'page')
    """
    # Note: Orders don't have user_id yet in the model
    # This is a placeholder for when we add user association
    queryset = Order.query.order_by(Order.id.desc())

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
            message="Orders retrieved successfully"

@bp.route('/products', methods=['GET', 'POST'])
def products_handler():
    """
    GET: List all products with pagination
    POST: Create a new product (admin only)

    Query params for GET:
        - page: Page number (for page-based pagination)
        - page_size: Items per page (for page-based pagination)
        - limit: Number of items (for limit/offset pagination)
        - offset: Starting position (for limit/offset pagination)
        - pagination_type: 'page' or 'limit_offset' (default: 'page')
    """
    if request.method == 'GET':
        queryset = Product.query.order_by(Product.id.asc())

        # Determine pagination type
        pagination_type = request.args.get('pagination_type', 'page')

        if pagination_type == 'limit_offset':
            return UnifiedPagination.paginate_by_limit_offset(
                queryset=queryset,
                serializer_func=lambda prod: prod.serialize(),
                message="Products retrieved successfully"
            )
        else:
            return UnifiedPagination.paginate_by_page(
                queryset=queryset,
                serializer_func=lambda prod: prod.serialize(),
                message="Products retrieved successfully"
            )

    elif request.method == 'POST':
        # Validate JSON request
        if not request.is_json:
            return UnifiedResponse.error(
                message="Request body should be in JSON format",
                status_code=400
            )

        body = request.get_json()

        # Validate required fields
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

    # Validate required fields
    required_fields = ['name', 'email', 'items']
    missing_fields = [field for field in required_fields if field not in body]

    if missing_fields:
        return UnifiedResponse.validation_error({
            'missing_fields': missing_fields,
            'message': 'Required fields: name, email, items'
        })

    if not isinstance(body['items'], list) or len(body['items']) == 0:
        return UnifiedResponse.validation_error({
            'items': 'items must be a non-empty list'
        })

    # Check on order [not empty]
    # apply atomicity for transaction -> all or none
    try:
        order = Order(
            name=body['name'],
            email=body['email'],
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
    Requires authentication.
    """
    order = db.session.get(Order, order_id)
    if not order:
        return UnifiedResponse.not_found(
            message=f"Order with ID {order_id} not found"
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
    Requires authentication.
    """
    order = db.session.get(Order, order_id)
    if not order:
        return UnifiedResponse.not_found(
            message=f"Order with ID {order_id} not found"
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


@bp.route('/orders/<int:order_id>', methods=['GET'])
@optional_auth
def get_order(order_id):
    """
    Get a specific order by ID.
    Available to all users (with optional auth).
    """
    order = db.session.get(Order, order_id)
    if not order:
        return UnifiedResponse.not_found(
            message=f"Order with ID {order_id} not found"
        )

    return UnifiedResponse.success(
        data=order.serialize(),
        message="Order retrieved successfully"
    )
