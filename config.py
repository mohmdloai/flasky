import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Mail Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

    # Celery Configuration
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'amqp://admin:admin@localhost:5672//')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True

    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 15))  # minutes
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 7))  # days

    # Session Configuration
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')  # Can be 'redis', 'sqlalchemy', 'filesystem'
    SESSION_PERMANENT = os.getenv('SESSION_PERMANENT', 'True') == 'True'
    SESSION_USE_SIGNER = os.getenv('SESSION_USE_SIGNER', 'True') == 'True'
    SESSION_KEY_PREFIX = os.getenv('SESSION_KEY_PREFIX', 'flasky_session:')
    SESSION_COOKIE_NAME = os.getenv('SESSION_COOKIE_NAME', 'flasky_session')
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True') == 'True'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')  # 'Strict', 'Lax', or 'None'
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.getenv('PERMANENT_SESSION_LIFETIME', 7)))

    # Redis Configuration (for session storage if using Redis)
    SESSION_REDIS = os.getenv('REDIS_URL', 'redis://localhost:6379/1')

    # Authentication Token Expiry Configuration
    EMAIL_VERIFICATION_EXPIRES = int(os.getenv('EMAIL_VERIFICATION_EXPIRES', 24))  # hours
    PASSWORD_RESET_EXPIRES = int(os.getenv('PASSWORD_RESET_EXPIRES', 1))  # hours

    # Frontend URL (for email links)
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

    # MinIO / S3 object storage
    # MINIO_ENDPOINT — used by the backend (container → container, e.g. http://minio:9000)
    # MINIO_PUBLIC_ENDPOINT — used when building URLs returned to the browser (e.g. http://localhost:9000)
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'http://localhost:9000')
    MINIO_PUBLIC_ENDPOINT = os.getenv('MINIO_PUBLIC_ENDPOINT', 'http://localhost:9000')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'flasky-admin')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'flasky-admin-change-me')
    MINIO_REGION = os.getenv('MINIO_REGION', 'us-east-1')
    MINIO_BUCKET_PRODUCTS = os.getenv('MINIO_BUCKET_PRODUCTS', 'products')
    MINIO_BUCKET_AVATARS = os.getenv('MINIO_BUCKET_AVATARS', 'avatars')
