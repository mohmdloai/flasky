from . import db
import enum
from sqlalchemy import Enum

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
            'items': [item.serialize() for item in self.items]
        }



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
