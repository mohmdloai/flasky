import pytest
from app.models import Product, Order, OrderItem, PaymentStatus, ShippingStatus


def test_create_products(client):
    products_data= [
        {"name": "Galaxy 26 Ultra", "price": 1299.99, "stock": 4},
        {"name": "MackBook Air", "price": 2299.99, "stock": 7},
        {"name": "MackBook Pro", "price": 3009.00, "stock": 9},
        {"name": "MackBook Pro Max", "price": 4000.00, "stock": 5},


    ]


    created_products = []
    for product_data in products_data:
        response = client.post('/api/products', json= product_data)
        assert response.status_code== 201
        product = response.get_json()
        assert product["name"] == product_data["name"]
        assert product["price"] == product_data["price"]
        assert product["stock"] == product_data["stock"]
        created_products.append(product)