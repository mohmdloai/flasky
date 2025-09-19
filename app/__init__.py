from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config.from_object(Config)
    CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

    db.init_app(app)
    mail.init_app(app)

    # Import and register routes
    from . import routes
    app.register_blueprint(routes.bp)

    return app