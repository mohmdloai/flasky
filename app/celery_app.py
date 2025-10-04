from celery import Celery
from celery.schedules import crontab
from config import Config

def make_celery(app_name='flasky'):
    celery = Celery(
        app_name,
        broker=Config.CELERY_BROKER_URL,
        backend=Config.CELERY_RESULT_BACKEND,
        include=['app.tasks']  # This tells Celery where to find tasks
    )

    celery.config_from_object(Config)

    # Celery Beat Schedule
    celery.conf.beat_schedule = {
        'check-low-stock-daily': {
            'task': 'app.tasks.check_low_stock',
            'schedule': crontab(hour=9, minute=0),
        },
        'cleanup-old-pending-orders': {
            'task': 'app.tasks.cleanup_old_pending_orders',
            'schedule': crontab(hour=0, minute=0),
        },
        'generate-daily-sales-report': {
            'task': 'app.tasks.generate_daily_sales_report',
            'schedule': crontab(hour=23, minute=0),
        },
        'cache-popular-products': {
            'task': 'app.tasks.cache_popular_products',
            'schedule': crontab(minute='*/30'),
        },
    }

    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )

    return celery

celery = make_celery()