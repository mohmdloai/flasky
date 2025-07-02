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