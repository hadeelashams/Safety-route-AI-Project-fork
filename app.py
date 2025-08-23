from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from db import db
from models import User, Destination
import os
import datetime

# Assuming you might need password hashing
# from werkzeug.security import generate_password_hash

from backend import auth_bp
from backend.login import login_routes
from backend.signup import signup_routes

app = Flask(__name__)

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345678@localhost/saferouteai'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)

db.init_app(app)

with app.app_context():
    db.create_all()

# --- Blueprints ---
login_routes()
signup_routes()
app.register_blueprint(auth_bp)

# --- Main Routes ---
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard():
    return render_template('user_dashboard.html')

# --- Admin Routes ---
@app.route('/admin')
def admin_base():
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/dashboard')
def admin_dashboard():
    total_users = User.query.count()
    total_destinations = Destination.query.count()
    top_search = Destination.query.order_by(Destination.Destination_id.desc()).first()
    return render_template('admin_dashboard.html', total_users=total_users, total_destinations=total_destinations, top_search_name=top_search.Name if top_search else "N/A", active_page='dashboard')

# --- Destination Management Routes ---
@app.route('/admin/manage_destination')
def manage_destination():
    destinations = Destination.query.all()
    return render_template('manage_destination.html', destinations=destinations, active_page='destinations')

@app.route('/admin/add-destination', methods=['POST'])
def api_add_destination():
    try:
        data = request.get_json()
        if not data or not data.get('name') or not data.get('place'):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        new_dest = Destination(Name=data.get('name'), Place=data.get('place'), Type=data.get('type'), Description=data.get('description'))
        db.session.add(new_dest)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Destination added successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500

@app.route('/admin/update-destination/<int:dest_id>', methods=['PUT'])
def api_update_destination(dest_id):
    try:
        dest = Destination.query.get(dest_id)
        if not dest:
            return jsonify({'success': False, 'message': 'Destination not found'}), 404
        data = request.get_json()
        dest.Name = data.get('name')
        dest.Place = data.get('place')
        dest.Type = data.get('type')
        dest.Description = data.get('description')
        db.session.commit()
        return jsonify({'success': True, 'message': 'Destination updated successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500

@app.route('/admin/delete-destination/<int:dest_id>', methods=['POST'])
def delete_destination(dest_id):
    try:
        dest = Destination.query.get_or_404(dest_id)
        db.session.delete(dest)
        db.session.commit()
        flash('Destination deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting destination: {str(e)}', 'danger')
    return redirect(url_for('manage_destination'))


# --- User Management Routes ---

@app.route('/admin/manage_users')
def manage_users():
    # This is the only line that has been changed.
    # It now filters the database to only get users with the role 'User'.
    users = User.query.filter_by(role='User').all()
    return render_template('manage_users.html', users=users, active_page='users')

@app.route('/admin/api/add-user', methods=['POST'])
def api_add_user():
    """Handles creating a new user from the modal's JSON data."""
    try:
        data = request.get_json()
        if not data or not data.get('username') or not data.get('email'):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        username = data.get('username')
        email = data.get('email')
        password = "defaultpassword123"

        if User.query.filter_by(Username=username).first():
            return jsonify({'success': False, 'message': f'Username "{username}" already exists.'}), 409
        if User.query.filter_by(Email=email).first():
            return jsonify({'success': False, 'message': f'Email "{email}" is already registered.'}), 409

        # New users will automatically get the default 'User' role from your model
        new_user = User(
            Username=username,
            Email=email,
            Password=password,
            name=username
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User added successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Handles deleting a user from the database."""
    try:
        user_to_delete = User.query.get_or_404(user_id)
        username = user_to_delete.Username
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'User "{username}" has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('manage_users'))

# --- Main Application Runner ---
if __name__ == '__main__':
    app.run(debug=True)