# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from db import db
from models import User # Assuming you have a User model
import datetime
import os

# Correct way to import the Blueprint object
from backend import auth_bp
# Import the functions that register routes with the blueprint
from backend.login import login_routes
from backend.signup import signup_routes

app = Flask(__name__)

# Basic Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345678@localhost/saferouteai'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24) # Set a strong secret key for session management
db.init_app(app)

with app.app_context():
    db.create_all() # Create database tables if they don't exist

# Now, call the functions to register the routes with the blueprint
login_routes()
signup_routes()

# Register the Blueprint after all routes are attached
app.register_blueprint(auth_bp)

# Route for the Landing Page (main entry point)
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard():
    # TODO: Implement protected dashboard content here
    # Use @login_required decorator from Flask-Login to protect this route
    return "<h1>Welcome to your Dashboard! (Protected Content)</h1>"

if __name__ == '__main__':
    app.run(debug=True)
