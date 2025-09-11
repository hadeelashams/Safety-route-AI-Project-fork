# backend/admin.py

from flask import render_template, redirect, url_for, request, jsonify, flash
from . import admin_bp
from models import db, User, Destination

# ### START: Define the canonical list of districts here ###
KERALA_DISTRICTS = [
    "Alappuzha", "Ernakulam", "Idukki", "Kannur", "Kasaragod", "Kollam",
    "Kottayam", "Kozhikode", "Malappuram", "Palakkad", "Pathanamthitta",
    "Thiruvananthapuram", "Thrissur", "Wayanad"
]
# ### END: District list ###


# --- Admin Dashboard ---
@admin_bp.route('/')
def base():
    # Redirect /admin to /admin/dashboard for a clean entry point
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/dashboard')
def dashboard():
    total_users = User.query.filter_by(role='user').count()
    total_destinations = Destination.query.count()
    return render_template('admin/admin_dashboard.html', 
                           total_users=total_users, 
                           total_destinations=total_destinations, 
                           top_search_name="N/A", # Added default value
                           active_page='dashboard')


# --- Destination Management Routes ---
@admin_bp.route('/manage_destination')
def manage_destination():
    destinations = Destination.query.all()
    # ### FIX: Pass the canonical district list to the template ###
    return render_template(
        'admin/manage_destination.html', 
        destinations=destinations, 
        all_districts=KERALA_DISTRICTS,  # Pass the list here
        active_page='destinations'
    )

# (The rest of the file remains unchanged)
@admin_bp.route('/add-destination', methods=['POST'])
def add_destination():
    """API endpoint to add a new destination."""
    try:
        data = request.get_json()
        if not all(k in data for k in ['name', 'place', 'type', 'description']):
            return jsonify({'success': False, 'message': 'Missing required fields.'}), 400
        
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

@admin_bp.route('/update-destination/<int:dest_id>', methods=['PUT'])
def update_destination(dest_id):
    """API endpoint to update an existing destination."""
    try:
        dest = Destination.query.get(dest_id)
        if not dest:
            return jsonify({'success': False, 'message': 'Destination not found'}), 404
        
        data = request.get_json()
        dest.Name = data.get('name', dest.Name)
        dest.Place = data.get('place', dest.Place)
        dest.Type = data.get('type', dest.Type)
        dest.Description = data.get('description', dest.Description)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Destination updated successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500

@admin_bp.route('/delete-destination/<int:dest_id>', methods=['POST'])
def delete_destination(dest_id):
    """Route to handle the deletion of a destination via a form post."""
    try:
        dest = Destination.query.get_or_404(dest_id)
        db.session.delete(dest)
        db.session.commit()
        flash('Destination deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting destination: {str(e)}', 'danger')
    return redirect(url_for('admin.manage_destination'))


# --- User Management Routes ---
@admin_bp.route('/manage_users')
def manage_users():
    users = User.query.filter_by(role='user').all()
    return render_template('admin/manage_users.html', users=users, active_page='users')

@admin_bp.route('/api/update-user/<int:user_id>', methods=['PUT'])
def api_update_user(user_id):
    try:
        user_to_update = User.query.get_or_404(user_id)
        data = request.get_json()

        if not data or not data.get('username') or not data.get('email'):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        user_to_update.Username = data['username']
        user_to_update.Email = data['email']
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'User updated successfully!'})
    except Exception as e:
        db.session.rollback()
        if 'Duplicate entry' in str(e):
            return jsonify({'success': False, 'message': 'Username or email already exists.'}), 409
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500

@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        user_to_delete = User.query.get_or_404(user_id)
        username = user_to_delete.Username
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'User "{username}" has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_users'))