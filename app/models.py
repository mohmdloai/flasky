from . import db
import enum
from sqlalchemy import Enum
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"

class ShippingStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"



# Product Rel Mapping
# - price
# - name
# - stock: int


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)

    # Cached review aggregates — kept in sync by Review insert/update/delete
    # so the product grid doesn't have to aggregate at query time.
    avg_rating = db.Column(db.Float, nullable=False, default=0.0)
    review_count = db.Column(db.Integer, nullable=False, default=0)

    images = db.relationship(
        'ProductImage',
        back_populates='product',
        cascade='all, delete-orphan',
        order_by='ProductImage.sort_order',
    )
    reviews = db.relationship(
        'Review',
        back_populates='product',
        cascade='all, delete-orphan',
    )

    def serialize(self, include_images=True):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'stock': self.stock,
            'avg_rating': round(self.avg_rating, 2),
            'review_count': self.review_count,
        }
        if include_images:
            data['images'] = [img.serialize() for img in self.images]
        return data


class ProductImage(db.Model):
    __tablename__ = 'product_image'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    bucket = db.Column(db.String(63), nullable=False)
    object_key = db.Column(db.String(512), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    product = db.relationship('Product', back_populates='images')

    def serialize(self):
        from app.utils.storage import build_public_url
        return {
            'id': self.id,
            'url': build_public_url(self.bucket, self.object_key),
            'sort_order': self.sort_order,
            'is_primary': self.is_primary,
        }


class Review(db.Model):
    __tablename__ = 'review'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)  # validated 1..5 at the route layer
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    product = db.relationship('Product', back_populates='reviews')
    user = db.relationship('User')

    __table_args__ = (
        # One review per (user, product) — change if you want users to edit instead.
        db.UniqueConstraint('user_id', 'product_id', name='uq_review_user_product'),
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='ck_review_rating_range'),
    )

    def serialize(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }




# Order Rel Mapping
# - payment_status -> pending, paid
# - payment_reference -> nullable string
# - shipping_status -> pending, in_progress, delivered
# - name
# - email
# - order_items <- back-ref


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_status = db.Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    payment_reference = db.Column(db.String(255), nullable=True)
    shipping_status =db.Column(Enum(ShippingStatus), default=ShippingStatus.PENDING, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    user = db.relationship('User', back_populates='orders')
    items = db.relationship('OrderItem', back_populates='order')

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'payment_status': self.payment_status.value,
            'payment_reference': self.payment_reference,
            'shipping_status': self.shipping_status.value,
            'name': self.name,
            'email': self.email,
            'items': [item.serialize() for item in self.items],
            'total_amount': self.total_amount
        }

    @property
    def total_amount(self):
        return sum(item.quantity * item.product.price for item in self.items)


# Map as normalization -> OrderItem
# - product: 12M => one OI has -> many Prods
# - quantity
# - order: FK

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    order = db.relationship('Order', back_populates='items') # => for objs level
    product = db.relationship('Product')

    def serialize(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'order_id': self.order_id,
            'quantity': self.quantity,
            'product': self.product.serialize() if self.product else None
        }


# ============= Authentication Models =============

class Role(db.Model):
    """User roles for RBAC (Role-Based Access Control)"""
    __tablename__ = 'role'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # e.g., 'admin', 'user', 'moderator'
    description = db.Column(db.String(255), nullable=True)
    permissions = db.Column(db.JSON, nullable=True)  # Store permissions as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    users = db.relationship('User', back_populates='role')

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'permissions': self.permissions
        }


class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Profile fields
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)

    # Status fields
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Avatar (single-slot: old object is deleted on re-upload)
    avatar_bucket = db.Column(db.String(63), nullable=True)
    avatar_object_key = db.Column(db.String(512), nullable=True)

    # Role relationship
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    role = db.relationship('Role', back_populates='users')

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    refresh_tokens = db.relationship('RefreshToken', back_populates='user', cascade='all, delete-orphan')
    email_verification_tokens = db.relationship('EmailVerificationToken', back_populates='user', cascade='all, delete-orphan')
    password_reset_tokens = db.relationship('PasswordResetToken', back_populates='user', cascade='all, delete-orphan')
    orders = db.relationship('Order', back_populates='user')

    def set_password(self, password: str):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)

    @property
    def avatar_url(self):
        if not self.avatar_bucket or not self.avatar_object_key:
            return None
        from app.utils.storage import build_public_url
        return build_public_url(self.avatar_bucket, self.avatar_object_key)

    def serialize(self, include_sensitive=False):
        """Serialize user data"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'avatar_url': self.avatar_url,
            'email_verified': self.email_verified,
            'is_active': self.is_active,
            'role': self.role.serialize() if self.role else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

        if include_sensitive:
            data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None

        return data


class RefreshToken(db.Model):
    """Refresh tokens for JWT authentication"""
    __tablename__ = 'refresh_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(500), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='refresh_tokens')

    def is_valid(self) -> bool:
        """Check if the refresh token is still valid"""
        return not self.revoked and self.expires_at > datetime.utcnow()

    def revoke(self):
        """Revoke the refresh token"""
        self.revoked = True


class EmailVerificationToken(db.Model):
    """Email verification tokens"""
    __tablename__ = 'email_verification_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='email_verification_tokens')

    def is_valid(self) -> bool:
        """Check if the token is still valid"""
        return not self.used and self.expires_at > datetime.utcnow()

    def mark_used(self):
        """Mark the token as used"""
        self.used = True


class PasswordResetToken(db.Model):
    """Password reset tokens"""
    __tablename__ = 'password_reset_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='password_reset_tokens')

    def is_valid(self) -> bool:
        """Check if the token is still valid"""
        return not self.used and self.expires_at > datetime.utcnow()

    def mark_used(self):
        """Mark the token as used"""
        self.used = True
