import pytest
from app.models import Product,db, Order, OrderItem, PaymentStatus, ShippingStatus

class TestOrderProcess:

    @pytest.fixture(autouse=True)
    def setup_products(self, client):
        self.client = client
        with client.application.app_context():
            products = [
                Product(name="Galaxy 26 Ultra", price=1299.99, stock=4),
                Product(name="MackBook Air", price=2299.99, stock=7),
                Product(name="MackBook Pro", price=3009.00, stock=9),
                Product(name="MackBook Pro Max", price=4000.00, stock=5),
            ]
            db.session.add_all(products)
            db.session.commit()

    def test_create_products(self):
        response = self.client.get('/api/products')
        assert response.status_code == 200
        products = response.get_json()
        assert len(products) == 4
        print(f"Created {len(products)}, can get all products successfully")
        print(products)


    def test_create_order_with_items(self, client):
        order_data= {
            "name": "me",
                "email": "me@gmail.com",
                "items": [
                    {"product_id": 1, "quantity": 3},
                    {"product_id": 2, "quantity": 3}
                ]
        }

        response = client.post('/api/orders', json= order_data)
        assert response.status_code == 201


        order = response.get_json()
        assert order["name"] == "me"
        assert order["email"] == "me@gmail.com"
        assert order['payment_status'] == "pending"
        assert order['shipping_status'] == "pending"
        assert len(order['items']) == 2


        response = client.get('/api/products')
        products = response.get_json()
        assert response.status_code == 200
        galaxy = next(prod for prod in products if prod['id'] == 1)
        macbook_air = next(prod for prod in products if prod['id'] == 2)
        assert galaxy['stock'] == 1
        assert macbook_air['stock'] == 4
        print(f"Created order with ID {order['id']}")
        print(f"Updated stock - Galaxy 26 Ultra: {galaxy['stock']}, MacBook Air: {macbook_air['stock']}")
