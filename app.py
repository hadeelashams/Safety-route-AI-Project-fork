from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from db import db
from models import User, Destination # Make sure to import your models
import os
import datetime # Make sure datetime is imported for your Destination model

# Blueprints (if you are using them)
from backend import auth_bp
from backend.login import login_routes
from backend.signup import signup_routes

app = Flask(__name__)

# -------------------
# Configuration
# -------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345678@localhost/saferouteai'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)

db.init_app(app)

# This is needed to create the tables based on your models
with app.app_context():
    db.create_all()

# -------------------
# Auth Blueprints (if used)
# -------------------
login_routes()
signup_routes()
app.register_blueprint(auth_bp)

# -------------------
# Routes
# -------------------

# Landing Page
@app.route('/')
def landing():
    return render_template('landing.html')

# User Dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('user_dashboard.html')

# MODIFIED: Redirect /admin to the admin dashboard for a clean entry point.
@app.route('/admin')
def admin_base():
    return redirect(url_for('admin_dashboard'))

# RENAMED and MODIFIED: This route now serves the full dashboard page.
@app.route('/admin/dashboard')
def admin_dashboard():
    total_users = User.query.count()
    total_destinations = Destination.query.count()
    top_search = Destination.query.order_by(Destination.Destination_id.desc()).first()
    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        total_destinations=total_destinations,
        top_search_name=top_search.Name if top_search else "N/A",
        active_page='dashboard'  # Pass active page identifier
    )

# -------------------
# Manage Destinations
# -------------------

# MODIFIED: Route now renders the full page for managing destinations.
@app.route('/admin/manage_destinations')
def manage_destinations():
    try:
        destinations = Destination.query.all()
        return render_template(
            'manage_destinations.html', 
            destinations=destinations,
            active_page='destinations' # Pass active page identifier
        )
    except Exception as e:
        print(f"Error loading destinations: {str(e)}")
        flash(f"Error loading destinations: {e}", "danger")
        return redirect(url_for('admin_dashboard'))


@app.route('/admin/add-destination', methods=['POST'])
def add_destination():
    try:
        data = request.get_json()
        if not all(key in data for key in ['name', 'place', 'type', 'description']):
            return jsonify({'success': False, 'message': 'Missing data'}), 400

        new_dest = Destination(
            Name=data['name'],
            Place=data['place'],
            Type=data['type'],
            Description=data['description']
        )
        db.session.add(new_dest)
        db.session.commit()

        # Return the newly created destination's data
        return jsonify({
            'success': True,
            'destination': {
                'Destination_id': new_dest.Destination_id,
                'Name': new_dest.Name,
                'Place': new_dest.Place,
                'Type': new_dest.Type,
                'Description': new_dest.Description
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/edit-destination/<int:dest_id>', methods=['GET', 'POST'])
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
            flash(f'Error updating destination: {str(e)}', 'error')
        return redirect(url_for('manage_destinations'))

    return render_template('edit_destination.html', destination=dest)


@app.route('/admin/delete-destination/<int:dest_id>', methods=['POST'])
def delete_destination(dest_id):
    try:
        dest = Destination.query.get_or_404(dest_id)
        db.session.delete(dest)
        db.session.commit()
        flash('Destination deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting destination: {str(e)}', 'error')
    
    return redirect(url_for('manage_destinations'))


# -------------------
# Manage Users
# -------------------
# MODIFIED: Route now renders the full page for managing users.
@app.route('/admin/manage_users')
def manage_users():
    users = User.query.all()
    return render_template(
        'manage_users.html', 
        users=users,
        active_page='users' # Pass active page identifier
    )

# -------------------
# Run Server
# -------------------
if __name__ == '__main__':
    app.run(debug=True)