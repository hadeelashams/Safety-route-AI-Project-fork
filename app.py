from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from db import db
from models import User, Destination
import os
import datetime

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

@app.route('/admin/manage_destination')
def manage_destination():
    destinations = Destination.query.all()
    return render_template('manage_destination.html', destinations=destinations, active_page='destinations')


# --- NEW API ENDPOINTS FOR THE JAVASCRIPT MODAL ---
# These routes handle the fetch() requests from your manage_destination.html page

@app.route('/admin/add-destination', methods=['POST'])
def api_add_destination():
    """Handles creating a new destination from the modal's JSON data."""
    try:
        data = request.get_json()
        if not data or not data.get('name') or not data.get('place'):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        new_dest = Destination(
            Name=data.get('name'),
            Place=data.get('place'),
            Type=data.get('type'),
            Description=data.get('description')
        )
        db.session.add(new_dest)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Destination added successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500


@app.route('/admin/update-destination/<int:dest_id>', methods=['PUT'])
def api_update_destination(dest_id):
    """Handles updating an existing destination from the modal's JSON data."""
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


# --- OLD FORM-BASED ROUTES (COMMENTED OUT) ---
# These routes were for a traditional multi-page form submission.
# They are no longer needed because the new modal and API endpoints handle this logic.
"""
@app.route('/admin/destination/add', methods=['GET', 'POST'])
def add_destination():
    if request.method == 'POST':
        try:
            new_dest = Destination(
                Name=request.form['name'],
                Place=request.form['place'],
                Type=request.form['type'],
                Description=request.form['description']
            )
            db.session.add(new_dest)
            db.session.commit()
            flash('Destination added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding destination: {str(e)}', 'danger')
        return redirect(url_for('manage_destination'))
    
    return render_template('destination_form.html', active_page='destinations')

@app.route('/admin/destination/edit/<int:dest_id>', methods=['GET', 'POST'])
def edit_destination(dest_id):
    dest = Destination.query.get_or_404(dest_id)
    if request.method == 'POST':
        try:
            dest.Name = request.form['name']
            dest.Place = request.form['place']
            dest.Type = request.form['type']
            dest.Description = request.form['description']
            db.session.commit()
            flash('Destination updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating destination: {str(e)}', 'danger')
        return redirect(url_for('manage_destination'))

    return render_template('destination_form.html', destination=dest, active_page='destinations')
"""

# The delete route is still correct because it uses a standard HTML form POST
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


@app.route('/admin/manage_users')
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users, active_page='users')


if __name__ == '__main__':
    app.run(debug=True)