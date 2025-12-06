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
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'stock': self.stock
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
    items = db.relationship('OrderItem', back_populates='order')

    def serialize(self):
        return {
            'id': self.id,
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

    def set_password(self, password: str):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)

    def serialize(self, include_sensitive=False):
        """Serialize user data"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
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
