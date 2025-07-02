from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from flask_mail import Mail
from config import Config

db = SQLAlchemy()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config.from_object(Config)
    
    db.init_app(app)
    mail.init_app(app)

    # Import and register routes
    from . import routes
    app.register_blueprint(routes.bp)

    return app