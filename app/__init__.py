from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_mail import Mail
from flask_session import Session
from config import Config

db = SQLAlchemy()
mail = Mail()
sess = Session()

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config.from_object(Config)

    # Enhanced CORS configuration with credentials support
    CORS(app,
         origins=["http://localhost:5173", "http://127.0.0.1:5173"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"],
         supports_credentials=True)  # Enable cookies for session auth

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    sess.init_app(app)

    # Import and register blueprints
    from . import routes
    from .auth_routes import auth_bp

    app.register_blueprint(routes.bp)
    app.register_blueprint(auth_bp)

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

        # Seed default roles if they don't exist
        from .models import Role
        if not Role.query.filter_by(name='admin').first():
            admin_role = Role(
                name='admin',
                description='Administrator with full permissions',
                permissions={'all': True}
            )
            db.session.add(admin_role)

        if not Role.query.filter_by(name='user').first():
            user_role = Role(
                name='user',
                description='Regular user with basic permissions',
                permissions={'read': True, 'create_order': True}
            )
            db.session.add(user_role)

        if not Role.query.filter_by(name='moderator').first():
            moderator_role = Role(
                name='moderator',
                description='Moderator with elevated permissions',
                permissions={'read': True, 'create_order': True, 'manage_products': True}
            )
            db.session.add(moderator_role)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.warning(f"Could not seed roles: {str(e)}")

    return app