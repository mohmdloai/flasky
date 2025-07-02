from flask import Blueprint, request, jsonify
from .models import Product, Order, OrderItem, PaymentStatus, ShippingStatus
from . import db
import random, string
from flask import abort
from app.helper import send_email


# api for order process:
# Endpoints
#   - POST api/orders
#     in: [{product_id:int, quantity: int}]
#     out: order details or failure with message
#   - POST api/orders/{order-id}/pay
#     out: order details (with updated fields:reference)

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/products', methods=['GET', 'POST'])
def products_handler():
    if request.method == 'GET':
        products = Product.query.all()
        return jsonify([prod.serialize() for prod in products])

    elif request.method=='POST':
        if not request.is_json:
            return jsonify({
                'error' : "request body should be in json format "
            }), 400

        body = request.get_json()
        if not body or not all(k in body for k in ['name', 'price', 'stock']):
            return jsonify({'error' : 'Not valid body ,required : name, price, stock'}),400

        try:
            product = Product(
                name=body['name'],
                price=body['price'],
                stock=body['stock']
            )
            db.session.add(product)
            db.session.commit()
            return jsonify(product.serialize()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to create product: {str(e)}'}), 500



# for orders

@bp.route('/orders', methods= ['POST'])
def create_order():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON format"}),400

    body = request.get_json()

    if not body or not all (k in body for k in ['name', 'email', 'items']):
        return jsonify({"error": "those fields must included : ['name', 'email', 'items']"}),400

    if not isinstance(body['items'],list) or len(body['items']) == 0:
        return jsonify({'error': 'items must be a non empty list'}), 400

    # Check on order [not empty]
    # apply atomicity for transaction -> all or none
    try:
        order = Order(
            name= body['name'],
            email= body['email'],
            payment_status= PaymentStatus.PENDING,
            shipping_status= ShippingStatus.PENDING
        )
        db.session.add(order)
        db.session.flush()
        for item in body['items']:
            if not all(k in item for k in ['product_id', 'quantity']):
                return jsonify({'error': 'Each item must have product_id and quantity'})
            product = db.session.get(Product, item['product_id'])
            if not product:
                return jsonify({'error': f'Product with ID {item["product_id"]} not found'}), 404
            if product.stock < item['quantity']:
                return jsonify({'error': f'Insufficient stock for product {product.name}. Available: {product.stock}'}) ,400
            order_item = OrderItem(
                order_id=order.id,
                product_id=item['product_id'],
                quantity=item['quantity']
            )

            product.stock -= item['quantity']
            db.session.add(order_item)

        db.session.commit()
        return jsonify(order.serialize()),201





    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create order: {str(e)}'}), 500


# for an existing order -> to add more items
@bp.route('/orders/<int:order_id>/items', methods=['POST'])

def add_more_items(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404, description=f"Order with ID {order_id} not found.")

    if order.payment_status == PaymentStatus.PAID:
        return jsonify({'error': 'Cannot add items to a paid order, please make another one if you want'}), 400
    if not request.is_json:
        return jsonify({"error": "Request must be JSON format"}),400

    data = request.get_json()

    data = request.get_json()
    if not data or not all(k in data for k in ['product_id', 'quantity']):
        return jsonify({'error': 'Missing required fields: product_id, quantity'}), 400

    product = db.session.get(Product, data['product_id'])
    if not product:
        abort(404, description=f"Product with ID {data['product_id']} not found.")
    if product.stock < data['quantity']:
        return jsonify({'error': f'Insufficient stock. Available: {product.stock}, Requested: {data["quantity"]}'}), 400

    try:
        order_item = OrderItem(
            order_id=order_id,
            product_id=data['product_id'],
            quantity=data['quantity']
        )

        product.stock -= data['quantity']

        db.session.add(order_item)
        db.session.commit()
        return jsonify(order_item.serialize()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to add item to order: {str(e)}'}), 500








@bp.route('/orders/<int:order_id>/pay', methods=['POST'])
def pay_order(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404, description=f"Order with ID {order_id} not found.")

    if order.payment_status == PaymentStatus.PAID:
        return jsonify({'error': 'Order already paid'}), 400

    if len(order.items) == 0:
        return jsonify({'error': 'Cannot pay for an order with no items'}), 400

    try:

        payment_reference = 'Ref_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        order.payment_status = PaymentStatus.PAID
        order.payment_reference = payment_reference

        db.session.commit()
        send_email(
            subject="Order Confirmation",
            to=order.email,
            template="email/order_confirmation.html",

            name = order.name,
            order_id=  order.id,
            payment_reference = order.payment_reference,
            total_amount= order.total_amount
)
        return jsonify({
            'message': 'Payment successful',
            'payment_reference': payment_reference,
            'order': order.serialize()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Payment failed: {str(e)}'}), 500



@bp.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404, description=f"Order with ID {order_id} not found.")

    return jsonify(order.serialize())