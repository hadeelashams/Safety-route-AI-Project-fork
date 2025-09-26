# backend/admin.py

from flask import render_template, redirect, url_for, request, jsonify, flash
from . import admin_bp
from models import db, User, Destination, SafetyRating
from sqlalchemy.orm import joinedload
from backend.auth import admin_required


KERALA_DISTRICTS = sorted([
    "Alappuzha", "Ernakulam", "Idukki", "Kannur", "Kasaragod", "Kollam",
    "Kottayam", "Kozhikode", "Malappuram", "Palakkad", "Pathanamthitta",
    "Thiruvananthapuram", "Thrissur", "Wayanad"
])

@admin_bp.route('/')
@admin_required
def base():
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_users = User.query.filter_by(role='user').count()
    total_destinations = Destination.query.count()
    top_search_name = "N/A"
    try:
        top_destination = Destination.query.order_by(Destination.search_count.desc()).first()
        if top_destination and top_destination.search_count > 0:
            top_search_name = top_destination.Place
    except Exception as e:
        print(f"Admin Dashboard WARNING: Could not calculate top location. Error: {e}")
    return render_template('admin/admin_dashboard.html', 
                           total_users=total_users, 
                           total_destinations=total_destinations, 
                           top_search_name=top_search_name,
                           active_page='dashboard')

@admin_bp.route('/manage_destination')
@admin_required
def manage_destination():
    destinations = Destination.query.all()
    return render_template('admin/manage_destination.html', destinations=destinations, all_districts=KERALA_DISTRICTS, active_page='destinations')

@admin_bp.route('/add-destination', methods=['POST'])
@admin_required
def add_destination():
    try:
        data = request.get_json()
        if not all(k in data for k in ['name', 'place', 'type', 'description', 'budget']):
            return jsonify({'success': False, 'message': 'Missing required fields.'}), 400
        
        new_dest = Destination(
            Name=data.get('name'), Place=data.get('place'),
            Type=data.get('type'), Description=data.get('description'),
            budget=data.get('budget'),
            image_url=data.get('image_url') # <-- ADDED
        )
        db.session.add(new_dest)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Destination added successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500

@admin_bp.route('/update-destination/<int:dest_id>', methods=['PUT'])
@admin_required
def update_destination(dest_id):
    try:
        dest = Destination.query.get(dest_id)
        if not dest:
            return jsonify({'success': False, 'message': 'Destination not found'}), 404
        
        data = request.get_json()
        dest.Name = data.get('name', dest.Name)
        dest.Place = data.get('place', dest.Place)
        dest.Type = data.get('type', dest.Type)
        dest.Description = data.get('description', dest.Description)
        dest.budget = data.get('budget', dest.budget)
        dest.image_url = data.get('image_url', dest.image_url) # <-- ADDED
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Destination updated successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500

# ... (rest of admin.py is unchanged) ...
@admin_bp.route('/delete-destination/<int:dest_id>', methods=['POST'])
@admin_required
def delete_destination(dest_id):
    try:
        dest = Destination.query.get_or_404(dest_id)
        db.session.delete(dest)
        db.session.commit()
        flash('Destination deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting destination: {str(e)}', 'danger')
    return redirect(url_for('admin.manage_destination'))


# --- Safety Monitor Routes ---
@admin_bp.route('/monitor')
@admin_required
def monitor():
    destinations = Destination.query.options(
        joinedload(Destination.safety_ratings)
    ).order_by(Destination.Destination_id).all()

    for dest in destinations:
        dest.safety_rating = dest.safety_ratings[0] if dest.safety_ratings else None

    return render_template('admin/monitor.html', 
                           all_districts=KERALA_DISTRICTS,
                           ratings=ratings_dict,
                           summary=summary_stats, # Pass the new stats to the template
                           active_page='monitor')

@admin_bp.route('/update-safety-rating/<int:dest_id>', methods=['POST'])
@admin_required
def update_safety_rating(dest_id):
    try:
        rating = SafetyRating.query.filter_by(district_name=district_name).first()
        if not rating:
            rating = SafetyRating(district_name=district_name)
            db.session.add(rating)

        rating.weather_risk = weather_risk
        rating.health_risk = health_risk
        rating.disaster_risk = disaster_risk

        avg_risk = (weather_risk + health_risk + disaster_risk) / 3
        if avg_risk <= 1.5: rating.overall_safety = "Very Safe"
        elif avg_risk <= 2.5: rating.overall_safety = "Safe"
        elif avg_risk <= 3.5: rating.overall_safety = "Moderate"
        else: rating.overall_safety = "Risky"
            
        db.session.commit()
        flash(f'Successfully updated safety rating for {district_name}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating safety rating for {district_name}: {str(e)}', 'danger')

    return redirect(url_for('admin.monitor'))


# ... (User Management routes are unchanged) ...
@admin_bp.route('/manage_users')
@admin_required
def manage_users():
    users = User.query.filter_by(role='user').all()
    return render_template('admin/manage_users.html', users=users, active_page='users')

@admin_bp.route('/api/update-user/<int:user_id>', methods=['PUT'])
@admin_required
def api_update_user(user_id):
    user_to_update = User.query.get_or_404(user_id)
    data = request.get_json()
    user_to_update.Username, user_to_update.Email = data['username'], data['email']
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    return redirect(url_for('admin.manage_users'))