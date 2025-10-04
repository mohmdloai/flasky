from app.celery_app import celery
from flask import current_app
from flask_mail import Message
from app import mail, db, create_app
from app.models import Order, Product, PaymentStatus, ShippingStatus, OrderItem
from datetime import datetime, timedelta
from sqlalchemy import func
import redis
import json
import os

# Initialize Redis client with environment variable support
def get_redis_client():
    redis_url = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    # Extract host and port from redis URL
    if redis_url.startswith('redis://'):
        redis_url = redis_url.replace('redis://', '')
        if '/' in redis_url:
            host_port, db = redis_url.split('/')
            if ':' in host_port:
                host, port = host_port.split(':')
            else:
                host, port = host_port, 6379
        else:
            host, port, db = redis_url, 6379, 0
    return redis.Redis(host=host, port=int(port), db=int(db), decode_responses=True)

redis_client = get_redis_client()

@celery.task(name='app.tasks.send_email_async')
def send_email_async(subject, to, html_content):
    """
    Asynchronous email sending task
    """
    try:
        msg = Message(subject, recipients=[to])
        msg.html = html_content
        mail.send(msg)
        return f"Email sent to {to}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


@celery.task(name='app.tasks.send_order_confirmation')
def send_order_confirmation(order_id):
    """
    Send order confirmation email
    """
    app = create_app()
    with app.app_context():
        from flask import render_template
        order = db.session.get(Order, order_id)
        if not order:
            return f"Order {order_id} not found"

        order_items = []
        for item in order.items:
            order_items.append({
                'product_name': item.product.name,
                'quantity': item.quantity,
                'price': item.product.price,
                'subtotal': item.product.price * item.quantity
            })

        html_content = render_template(
            'email/order_confirmation.html',
            name=order.name,
            order_id=order.id,
            payment_reference=order.payment_reference,
            total_amount=order.total_amount,
            items=order_items
        )

        return send_email_async.delay(
            "Order Confirmation",
            order.email,
            html_content
        )


@celery.task(name='app.tasks.check_low_stock')
def check_low_stock():
    """
    Check for products with low stock and send alerts
    Runs daily via Celery Beat
    """
    app = create_app()
    with app.app_context():
        low_stock_threshold = 5
        products = Product.query.filter(Product.stock <= low_stock_threshold).all()

        if products:
            low_stock_list = [
                f"{p.name} - Stock: {p.stock}" for p in products
            ]

            # Store in Redis for quick access
            redis_client.setex(
                'low_stock_products',
                86400,  # 24 hours
                json.dumps(low_stock_list)
            )

            # Send email alert (if admin email is configured)
            admin_email = current_app.config.get('MAIL_USERNAME')
            if admin_email:
                html_content = f"""
                <h2>Low Stock Alert</h2>
                <p>The following products are running low on stock:</p>
                <ul>
                    {"".join([f"<li>{item}</li>" for item in low_stock_list])}
                </ul>
                """
                send_email_async.delay(
                    "Low Stock Alert",
                    admin_email,
                    html_content
                )

            return f"Found {len(products)} products with low stock"
        return "All products have sufficient stock"


@celery.task(name='app.tasks.cleanup_old_pending_orders')
def cleanup_old_pending_orders():
    """
    Delete pending orders older than 7 days
    Runs daily via Celery Beat
    """
    app = create_app()
    with app.app_context():
        cutoff_date = datetime.utcnow() - timedelta(days=7)

        # Note: You'll need to add created_at field to Order model
        # For now, this is a placeholder
        old_orders = Order.query.filter(
            Order.payment_status == PaymentStatus.PENDING
        ).all()

        count = 0
        for order in old_orders:
            # Restore stock
            for item in order.items:
                item.product.stock += item.quantity

            db.session.delete(order)
            count += 1

        db.session.commit()

        # Cache the cleanup result
        redis_client.setex(
            'last_cleanup',
            86400,
            json.dumps({
                'timestamp': datetime.utcnow().isoformat(),
                'orders_deleted': count
            })
        )

        return f"Deleted {count} old pending orders"


@celery.task(name='app.tasks.generate_daily_sales_report')
def generate_daily_sales_report():
    """
    Generate daily sales report and cache in Redis
    Runs daily via Celery Beat
    """
    app = create_app()
    with app.app_context():
        today = datetime.utcnow().date()

        # Get paid orders (you'll need to add created_at to Order model)
        paid_orders = Order.query.filter(
            Order.payment_status == PaymentStatus.PAID
        ).all()

        total_revenue = sum(order.total_amount for order in paid_orders)
        total_orders = len(paid_orders)

        # Get top selling products
        from sqlalchemy import func
        top_products = db.session.query(
            Product.name,
            func.sum(db.session.query(func.sum(OrderItem.quantity))
                    .filter(OrderItem.product_id == Product.id)
                    .correlate(Product)
                    .scalar_subquery()).label('total_sold')
        ).group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()

        report = {
            'date': str(today),
            'total_revenue': float(total_revenue),
            'total_orders': total_orders,
            'top_products': [
                {'name': name, 'sold': int(sold or 0)}
                for name, sold in top_products
            ]
        }

        # Cache in Redis for 30 days
        redis_client.setex(
            f'sales_report:{today}',
            2592000,
            json.dumps(report)
        )

        return report


@celery.task(name='app.tasks.cache_popular_products')
def cache_popular_products():
    """
    Cache popular products in Redis
    Runs every 30 minutes via Celery Beat
    """
    app = create_app()
    with app.app_context():
        from sqlalchemy import func
        from app.models import OrderItem

        # Get products ordered in the last 7 days
        popular = db.session.query(
            Product.id,
            Product.name,
            Product.price,
            Product.stock,
            func.count(OrderItem.id).label('order_count')
        ).join(OrderItem).group_by(Product.id).order_by(
            func.count(OrderItem.id).desc()
        ).limit(10).all()

        popular_list = [
            {
                'id': p.id,
                'name': p.name,
                'price': float(p.price),
                'stock': p.stock,
                'order_count': p.order_count
            }
            for p in popular
        ]

        redis_client.setex(
            'popular_products',
            1800,  # 30 minutes
            json.dumps(popular_list)
        )

        return f"Cached {len(popular_list)} popular products"


@celery.task(name='app.tasks.update_order_status')
def update_order_status(order_id, new_status):
    """
    Update order shipping status asynchronously
    """
    app = create_app()
    with app.app_context():
        order = db.session.get(Order, order_id)
        if order:
            order.shipping_status = ShippingStatus(new_status)
            db.session.commit()

            # Send notification email
            html_content = f"""
            <h2>Order Status Update</h2>
            <p>Dear {order.name},</p>
            <p>Your order #{order.id} status has been updated to: <strong>{new_status}</strong></p>
            """
            send_email_async.delay(
                f"Order #{order.id} Status Update",
                order.email,
                html_content
            )

            return f"Updated order {order_id} status to {new_status}"
        return f"Order {order_id} not found"