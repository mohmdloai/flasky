"""
Admin routes blueprint.
All endpoints require admin role.
"""
from flask import Blueprint, request, g
from app import db
from app.models import User, Role, Order, OrderItem, Product, PaymentStatus, ShippingStatus
from app.utils.response import UnifiedResponse
from app.utils.pagination import UnifiedPagination
from app.utils.decorators import auth_required, role_required


admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def _count_active_admins() -> int:
    return (
        User.query.join(Role)
        .filter(Role.name == 'admin', User.is_active == True)  # noqa: E712
        .count()
    )


#  Dashboard Stats 

@admin_bp.route('/stats', methods=['GET'])
@auth_required
@role_required(['admin'])
def get_stats():
    """Return aggregate counters for the admin dashboard."""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    verified_users = User.query.filter_by(email_verified=True).count()

    total_orders = Order.query.count()
    pending_shipping = Order.query.filter_by(shipping_status=ShippingStatus.PENDING).count()
    in_progress_shipping = Order.query.filter_by(shipping_status=ShippingStatus.IN_PROGRESS).count()
    delivered = Order.query.filter_by(shipping_status=ShippingStatus.DELIVERED).count()
    paid_orders = Order.query.filter_by(payment_status=PaymentStatus.PAID).count()
    unpaid_orders = Order.query.filter_by(payment_status=PaymentStatus.PENDING).count()

    paid_qs = Order.query.filter_by(payment_status=PaymentStatus.PAID).all()
    total_revenue = sum(o.total_amount for o in paid_qs)

    total_products = Product.query.count()
    low_stock_products = Product.query.filter(Product.stock < 10).count()
    out_of_stock = Product.query.filter(Product.stock == 0).count()

    return UnifiedResponse.success(
        data={
            'users': {
                'total': total_users,
                'active': active_users,
                'inactive': total_users - active_users,
                'verified': verified_users,
            },
            'orders': {
                'total': total_orders,
                'pending_shipping': pending_shipping,
                'in_progress_shipping': in_progress_shipping,
                'delivered': delivered,
                'paid': paid_orders,
                'unpaid': unpaid_orders,
            },
            'revenue': round(total_revenue, 2),
            'products': {
                'total': total_products,
                'low_stock': low_stock_products,
                'out_of_stock': out_of_stock,
            },
        },
        message='Stats retrieved successfully',
    )


#  Roles 

@admin_bp.route('/roles', methods=['GET'])
@auth_required
@role_required(['admin'])
def list_roles():
    roles = Role.query.order_by(Role.id.asc()).all()
    return UnifiedResponse.success(
        data=[r.serialize() for r in roles],
        message='Roles retrieved successfully',
    )


#  Users 

@admin_bp.route('/users', methods=['GET'])
@auth_required
@role_required(['admin'])
def list_users():
    """List users with search/filter/pagination."""
    search = request.args.get('search', '').strip()
    role_name = request.args.get('role')
    is_active = request.args.get('is_active')

    queryset = User.query.join(Role)

    if search:
        like = f'%{search}%'
        queryset = queryset.filter(
            (User.username.ilike(like))
            | (User.email.ilike(like))
            | (User.first_name.ilike(like))
            | (User.last_name.ilike(like))
        )

    if role_name:
        queryset = queryset.filter(Role.name == role_name)

    if is_active is not None and is_active != '':
        queryset = queryset.filter(User.is_active == (is_active.lower() == 'true'))

    queryset = queryset.order_by(User.created_at.desc())

    return UnifiedPagination.paginate_by_page(
        queryset=queryset,
        serializer_func=lambda u: u.serialize(),
        message='Users retrieved successfully',
    )


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@auth_required
@role_required(['admin'])
def get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return UnifiedResponse.not_found(message='User not found')
    return UnifiedResponse.success(data=user.serialize(), message='User retrieved successfully')


@admin_bp.route('/users/<int:user_id>', methods=['PATCH'])
@auth_required
@role_required(['admin'])
def update_user(user_id):
    """
    Update a user. Body may include any of:
        role_id, is_active, first_name, last_name
    """
    user = db.session.get(User, user_id)
    if not user:
        return UnifiedResponse.not_found(message='User not found')

    if not request.is_json:
        return UnifiedResponse.error(message='Request must be JSON format', status_code=400)

    data = request.get_json() or {}

    is_self = user.id == g.current_user.id

    if is_self and 'role_id' in data and data['role_id'] != user.role_id:
        return UnifiedResponse.error(
            message='You cannot change your own role',
            error_code='SELF_DEMOTION_BLOCKED',
            status_code=403,
        )

    if is_self and 'is_active' in data and not bool(data['is_active']):
        return UnifiedResponse.error(
            message='You cannot deactivate your own account',
            error_code='SELF_DEACTIVATION_BLOCKED',
            status_code=403,
        )

    # Last-admin lockout
    if 'role_id' in data and user.role and user.role.name == 'admin':
        new_role = db.session.get(Role, data['role_id'])
        if new_role and new_role.name != 'admin' and _count_active_admins() <= 1:
            return UnifiedResponse.error(
                message='Cannot demote the last active admin',
                error_code='LAST_ADMIN',
                status_code=403,
            )

    if (
        'is_active' in data
        and not bool(data['is_active'])
        and user.role
        and user.role.name == 'admin'
        and user.is_active
        and _count_active_admins() <= 1
    ):
        return UnifiedResponse.error(
            message='Cannot deactivate the last active admin',
            error_code='LAST_ADMIN',
            status_code=403,
        )

    try:
        if 'role_id' in data:
            new_role = db.session.get(Role, data['role_id'])
            if not new_role:
                return UnifiedResponse.validation_error({'role_id': 'Role not found'})
            user.role_id = new_role.id

        if 'is_active' in data:
            user.is_active = bool(data['is_active'])

        if 'first_name' in data:
            user.first_name = data['first_name']

        if 'last_name' in data:
            user.last_name = data['last_name']

        db.session.commit()

        return UnifiedResponse.success(
            data=user.serialize(),
            message='User updated successfully',
        )
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to update user: {str(e)}',
            status_code=500,
        )


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@auth_required
@role_required(['admin'])
def deactivate_user(user_id):
    """Soft delete — sets is_active=False."""
    user = db.session.get(User, user_id)
    if not user:
        return UnifiedResponse.not_found(message='User not found')

    if user.id == g.current_user.id:
        return UnifiedResponse.error(
            message='You cannot deactivate your own account',
            error_code='SELF_DELETE_BLOCKED',
            status_code=403,
        )

    if user.role and user.role.name == 'admin' and user.is_active and _count_active_admins() <= 1:
        return UnifiedResponse.error(
            message='Cannot deactivate the last active admin',
            error_code='LAST_ADMIN',
            status_code=403,
        )

    try:
        user.is_active = False
        db.session.commit()
        return UnifiedResponse.success(
            data=user.serialize(),
            message='User deactivated successfully',
        )
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to deactivate user: {str(e)}',
            status_code=500,
        )


#  Orders

@admin_bp.route('/orders', methods=['GET'])
@auth_required
@role_required(['admin', 'moderator'])
def list_orders():
    """List all orders with filters/search/pagination."""
    payment_filter = request.args.get('payment_status')
    shipping_filter = request.args.get('shipping_status')
    search = request.args.get('search', '').strip()

    queryset = Order.query

    if payment_filter:
        try:
            queryset = queryset.filter(Order.payment_status == PaymentStatus(payment_filter))
        except ValueError:
            return UnifiedResponse.validation_error({
                'payment_status': f"Must be one of: {', '.join(s.value for s in PaymentStatus)}"
            })

    if shipping_filter:
        try:
            queryset = queryset.filter(Order.shipping_status == ShippingStatus(shipping_filter))
        except ValueError:
            return UnifiedResponse.validation_error({
                'shipping_status': f"Must be one of: {', '.join(s.value for s in ShippingStatus)}"
            })

    if search:
        like = f'%{search}%'
        queryset = queryset.filter(
            (Order.name.ilike(like)) | (Order.email.ilike(like))
        )

    queryset = queryset.order_by(Order.id.desc())

    return UnifiedPagination.paginate_by_page(
        queryset=queryset,
        serializer_func=lambda o: o.serialize(),
        message='Orders retrieved successfully',
    )


#  Products 

@admin_bp.route('/products/<int:product_id>', methods=['PATCH'])
@auth_required
@role_required(['admin', 'moderator'])
def update_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return UnifiedResponse.not_found(message='Product not found')

    if not request.is_json:
        return UnifiedResponse.error(message='Request must be JSON format', status_code=400)

    data = request.get_json() or {}

    try:
        if 'name' in data:
            product.name = data['name']
        if 'price' in data:
            product.price = float(data['price'])
        if 'stock' in data:
            product.stock = int(data['stock'])

        db.session.commit()
        return UnifiedResponse.success(
            data=product.serialize(),
            message='Product updated successfully',
        )
    except (ValueError, TypeError) as e:
        db.session.rollback()
        return UnifiedResponse.validation_error({'message': f'Invalid value: {str(e)}'})
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to update product: {str(e)}',
            status_code=500,
        )


@admin_bp.route('/products/<int:product_id>', methods=['DELETE'])
@auth_required
@role_required(['admin', 'moderator'])
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return UnifiedResponse.not_found(message='Product not found')

    # Block deletion if referenced by any order item — would orphan FK
    has_items = OrderItem.query.filter_by(product_id=product_id).first() is not None
    if has_items:
        return UnifiedResponse.error(
            message='Cannot delete product referenced by existing orders',
            error_code='PRODUCT_IN_USE',
            status_code=400,
        )

    try:
        db.session.delete(product)
        db.session.commit()
        return UnifiedResponse.deleted(message='Product deleted successfully')
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to delete product: {str(e)}',
            status_code=500,
        )
