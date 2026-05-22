"""
Admin routes blueprint.
All endpoints require admin role.
"""
from flask import Blueprint, current_app, request, g
from app import db
from app.models import User, Role, Order, OrderItem, Product, ProductImage, PaymentStatus, ShippingStatus
from app.utils.response import UnifiedResponse
from app.utils.pagination import UnifiedPagination
from app.utils.decorators import auth_required, role_required
from app.utils.storage import (
    upload_fileobj,
    delete_object,
    generate_object_key,
    generate_presigned_put,
)


ALLOWED_IMAGE_MIME = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


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


#  Product images

@admin_bp.route('/products/<int:product_id>/images', methods=['POST'])
@auth_required
@role_required(['admin', 'moderator'])
def upload_product_image(product_id):
    """
    Multipart upload: field name "file". Optional form fields:
        - is_primary: "true" to mark as the product's primary image
        - sort_order: int

    For very large files / many concurrent uploads, swap to the presigned-PUT
    endpoint below so MinIO takes the bytes directly.
    """
    product = db.session.get(Product, product_id)
    if not product:
        return UnifiedResponse.not_found(message='Product not found')

    file = request.files.get('file')
    if not file:
        return UnifiedResponse.validation_error({'file': 'file is required (multipart/form-data)'})

    if file.mimetype not in ALLOWED_IMAGE_MIME:
        return UnifiedResponse.validation_error({
            'file': f"Unsupported type {file.mimetype}; allowed: {', '.join(sorted(ALLOWED_IMAGE_MIME))}"
        })

    # Size check — read once via stream so we don't load the whole file twice.
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_IMAGE_BYTES:
        return UnifiedResponse.validation_error({
            'file': f'File too large ({size} bytes); max {MAX_IMAGE_BYTES}'
        })

    is_primary = (request.form.get('is_primary', '').lower() == 'true')
    try:
        sort_order = int(request.form.get('sort_order', 0))
    except ValueError:
        return UnifiedResponse.validation_error({'sort_order': 'must be an integer'})

    bucket = current_app.config['MINIO_BUCKET_PRODUCTS']
    key = generate_object_key(f'product-{product_id}', file.filename or 'image.bin')

    try:
        upload_fileobj(bucket, key, file.stream, content_type=file.mimetype)
    except Exception as e:
        return UnifiedResponse.error(
            message=f'Upload to storage failed: {str(e)}',
            status_code=502,
        )

    try:
        if is_primary:
            # Demote any existing primary — UI invariant: at most one primary per product.
            ProductImage.query.filter_by(product_id=product_id, is_primary=True).update(
                {'is_primary': False}
            )

        image = ProductImage(
            product_id=product_id,
            bucket=bucket,
            object_key=key,
            sort_order=sort_order,
            is_primary=is_primary,
        )
        db.session.add(image)
        db.session.commit()
        return UnifiedResponse.created(
            data=image.serialize(),
            message='Image uploaded successfully',
            resource_id=image.id,
        )
    except Exception as e:
        db.session.rollback()
        # DB write failed after object was uploaded — best-effort cleanup to avoid orphaned blobs.
        delete_object(bucket, key)
        return UnifiedResponse.error(
            message=f'Failed to record image: {str(e)}',
            status_code=500,
        )


@admin_bp.route('/products/<int:product_id>/images/presign', methods=['POST'])
@auth_required
@role_required(['admin', 'moderator'])
def presign_product_image(product_id):
    """
    Alternative upload flow: returns a signed PUT URL the browser uses directly.
    Browser then calls POST /images/confirm with the returned object_key.
    Use this for big files where you don't want to proxy through Flask.
    """
    product = db.session.get(Product, product_id)
    if not product:
        return UnifiedResponse.not_found(message='Product not found')

    data = request.get_json(silent=True) or {}
    filename = data.get('filename', 'image.bin')
    bucket = current_app.config['MINIO_BUCKET_PRODUCTS']
    key = generate_object_key(f'product-{product_id}', filename)

    try:
        url = generate_presigned_put(bucket, key, expires_in=600)
    except Exception as e:
        return UnifiedResponse.error(
            message=f'Failed to generate presigned URL: {str(e)}',
            status_code=502,
        )

    return UnifiedResponse.success(
        data={'upload_url': url, 'bucket': bucket, 'object_key': key, 'expires_in': 600},
        message='Presigned URL generated',
    )


@admin_bp.route('/products/<int:product_id>/images/confirm', methods=['POST'])
@auth_required
@role_required(['admin', 'moderator'])
def confirm_product_image(product_id):
    """Pairs with /images/presign — call after the browser has PUT the file."""
    product = db.session.get(Product, product_id)
    if not product:
        return UnifiedResponse.not_found(message='Product not found')

    data = request.get_json(silent=True) or {}
    object_key = data.get('object_key')
    if not object_key:
        return UnifiedResponse.validation_error({'object_key': 'object_key is required'})

    bucket = data.get('bucket') or current_app.config['MINIO_BUCKET_PRODUCTS']
    is_primary = bool(data.get('is_primary'))
    try:
        sort_order = int(data.get('sort_order', 0))
    except (TypeError, ValueError):
        return UnifiedResponse.validation_error({'sort_order': 'must be an integer'})

    try:
        if is_primary:
            ProductImage.query.filter_by(product_id=product_id, is_primary=True).update(
                {'is_primary': False}
            )

        image = ProductImage(
            product_id=product_id,
            bucket=bucket,
            object_key=object_key,
            sort_order=sort_order,
            is_primary=is_primary,
        )
        db.session.add(image)
        db.session.commit()
        return UnifiedResponse.created(
            data=image.serialize(),
            message='Image registered successfully',
            resource_id=image.id,
        )
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to register image: {str(e)}',
            status_code=500,
        )


@admin_bp.route('/products/<int:product_id>/images/<int:image_id>', methods=['PATCH'])
@auth_required
@role_required(['admin', 'moderator'])
def update_product_image(product_id, image_id):
    """Patch sort_order or is_primary on an existing image. Demotes any other
    primary on the same product when this one is promoted — the UI invariant
    is at most one primary per product."""
    image = db.session.get(ProductImage, image_id)
    if not image or image.product_id != product_id:
        return UnifiedResponse.not_found(message='Image not found')

    if not request.is_json:
        return UnifiedResponse.error(message='Request must be JSON format', status_code=400)

    data = request.get_json() or {}

    try:
        if 'is_primary' in data:
            promote = bool(data['is_primary'])
            if promote:
                ProductImage.query.filter(
                    ProductImage.product_id == product_id,
                    ProductImage.id != image_id,
                    ProductImage.is_primary == True,  # noqa: E712
                ).update({'is_primary': False})
            image.is_primary = promote

        if 'sort_order' in data:
            image.sort_order = int(data['sort_order'])

        db.session.commit()
        return UnifiedResponse.success(
            data=image.serialize(),
            message='Image updated successfully',
        )
    except (TypeError, ValueError) as e:
        db.session.rollback()
        return UnifiedResponse.validation_error({'message': f'Invalid value: {str(e)}'})
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to update image: {str(e)}',
            status_code=500,
        )


@admin_bp.route('/products/<int:product_id>/images/<int:image_id>', methods=['DELETE'])
@auth_required
@role_required(['admin', 'moderator'])
def delete_product_image(product_id, image_id):
    image = db.session.get(ProductImage, image_id)
    if not image or image.product_id != product_id:
        return UnifiedResponse.not_found(message='Image not found')

    bucket, key = image.bucket, image.object_key
    try:
        db.session.delete(image)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to delete image record: {str(e)}',
            status_code=500,
        )

    # Storage deletion is best-effort and after DB commit — a stale blob is
    # less bad than a phantom DB row pointing at a deleted object.
    delete_object(bucket, key)
    return UnifiedResponse.deleted(message='Image deleted successfully')


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

    # Capture blob refs BEFORE delete — the cascade will wipe ProductImage rows
    # along with the product, so we'd lose the keys we need to clean up storage.
    blobs = [(img.bucket, img.object_key) for img in product.images]

    try:
        db.session.delete(product)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to delete product: {str(e)}',
            status_code=500,
        )

    # Best-effort blob cleanup after the DB commit. If storage is briefly down,
    # we'd rather have orphaned blobs than a half-rolled-back delete.
    for bucket, key in blobs:
        delete_object(bucket, key)

    return UnifiedResponse.deleted(message='Product deleted successfully')
