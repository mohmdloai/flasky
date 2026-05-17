from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_mail import Mail
from flask_session import Session
from config import Config

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
sess = Session()

# Importing the models module for its side effect: it registers every model class
# with db.metadata, which Alembic's autogenerate scans when producing migrations.
# Without this, `flask db migrate` would emit empty migrations.
from . import models  # noqa: F401, E402

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
    # render_as_batch=True lets Alembic alter columns on SQLite via the table-rebuild idiom
    migrate.init_app(app, db, render_as_batch=True)
    mail.init_app(app)
    sess.init_app(app)

    # Import and register blueprints
    from . import routes
    from .auth_routes import auth_bp

    app.register_blueprint(routes.bp)
    app.register_blueprint(auth_bp)

    # Seed default roles if they don't exist.
    # Wrapped in try/except so this is safe on a brand-new DB that hasn't been migrated yet
    # (e.g. before the first `flask db upgrade`).
    with app.app_context():
        from .models import Role
        try:
            if not Role.query.filter_by(name='admin').first():
                db.session.add(Role(
                    name='admin',
                    description='Administrator with full permissions',
                    permissions={'all': True},
                ))
            if not Role.query.filter_by(name='user').first():
                db.session.add(Role(
                    name='user',
                    description='Regular user with basic permissions',
                    permissions={'read': True, 'create_order': True},
                ))
            if not Role.query.filter_by(name='moderator').first():
                db.session.add(Role(
                    name='moderator',
                    description='Moderator with elevated permissions',
                    permissions={'read': True, 'create_order': True, 'manage_products': True},
                ))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.warning(f"Could not seed roles (run `flask db upgrade` first?): {str(e)}")

    return app