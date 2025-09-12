# app.py

from flask import Flask
from db import db
import os
from dotenv import load_dotenv # <-- ADD THIS LINE

load_dotenv() # <-- ADD THIS LINE to load variables from .env

# Import blueprints from the backend package
from backend.auth import auth_bp
from backend.views import views_bp
from backend.admin import admin_bp
from backend.aiservice import ai_bp

def create_app():
    """Application Factory Pattern"""
    app = Flask(__name__)

    # --- Configuration ---
    # Try to import local (ignored) config, otherwise fallback to environment/defaults
    try:
        import config_local as local_config
    except Exception:
        local_config = None

    # Database URI
    app.config['SQLALCHEMY_DATABASE_URI'] = local_config.SQLALCHEMY_DATABASE_URI

    # Track modifications
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Secret key
    if local_config and getattr(local_config, 'SECRET_KEY', None):
        app.config['SECRET_KEY'] = local_config.SECRET_KEY
    else:
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

    # ### ADDED: Load Gemini API Key into Flask config ###
    if local_config and getattr(local_config, 'GEMINI_API_KEY', None):
        app.config['GEMINI_API_KEY'] = local_config.GEMINI_API_KEY
    else:
        app.config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')

    # --- Initialize Extensions ---
    db.init_app(app)

    # --- Register Blueprints ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)

    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)