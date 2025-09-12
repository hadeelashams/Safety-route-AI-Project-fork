# app.py

from flask import Flask
from db import db
import os

# Import blueprints from the backend package
from backend.auth import auth_bp
from backend.views import views_bp
from backend.admin import admin_bp
from backend.aiservice import ai_bp

def create_app():
    """Application Factory Pattern"""
    app = Flask(__name__)

    # --- Configuration ---
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1234@localhost/saferouteai'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.urandom(24)

    # --- Initialize Extensions ---
    db.init_app(app)

    # --- Register Blueprints ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp) # Your AI service is already a blueprint!

    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)