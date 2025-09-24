# backend/admin.py

from flask import render_template, redirect, url_for, request, jsonify, flash
from . import admin_bp
from models import db, User, Destination, SafetyRating
import pandas as pd

KERALA_DISTRICTS = sorted([
    "Alappuzha", "Ernakulam", "Idukki", "Kannur", "Kasaragod", "Kollam",
    "Kottayam", "Kozhikode", "Malappuram", "Palakkad", "Pathanamthitta",
    "Thiruvananthapuram", "Thrissur", "Wayanad"
])

# ... (Dashboard, Destination Management routes are unchanged) ...
@admin_bp.route('/')
def base(): return redirect(url_for('admin.dashboard'))

@admin_bp.route('/dashboard')
def dashboard():
    total_users = User.query.filter_by(role='user').count()
    total_destinations = Destination.query.count()
    top_search_name = "N/A"
    try:
        csv_path = 'static/data/risklog.csv'
        risk_log_df = pd.read_csv(csv_path)
        if not risk_log_df.empty and 'destination_id' in risk_log_df.columns:
            top_destination_id = risk_log_df['destination_id'].mode()[0]
            top_destination = Destination.query.get(int(top_destination_id))
            if top_destination: top_search_name = top_destination.Place
    except Exception: pass
    return render_template('admin/admin_dashboard.html', total_users=total_users, total_destinations=total_destinations, top_search_name=top_search_name, active_page='dashboard')

@admin_bp.route('/manage_destination')
def manage_destination():
    destinations = Destination.query.all()
    return render_template('admin/manage_destination.html', destinations=destinations, all_districts=KERALA_DISTRICTS, active_page='destinations')

@admin_bp.route('/add-destination', methods=['POST'])
def add_destination():
    data = request.get_json()
    new_dest = Destination(Name=data['name'], Place=data['place'], Type=data['type'], Description=data['description'], budget=data['budget'])
    db.session.add(new_dest)
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/update-destination/<int:dest_id>', methods=['PUT'])
def update_destination(dest_id):
    dest = Destination.query.get_or_404(dest_id)
    data = request.get_json()
    dest.Name, dest.Place, dest.Type, dest.Description, dest.budget = data['name'], data['place'], data['type'], data['description'], data['budget']
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/delete-destination/<int:dest_id>', methods=['POST'])
def delete_destination(dest_id):
    dest = Destination.query.get_or_404(dest_id)
    db.session.delete(dest)
    db.session.commit()
    return redirect(url_for('admin.manage_destination'))


# ### START: UPDATED SAFETY MONITOR LOGIC ###
@admin_bp.route('/monitor')
def monitor():
    """Displays the upgraded district safety monitor page with summary stats."""
    all_ratings = SafetyRating.query.all()
    ratings_dict = {rating.district_name: rating for rating in all_ratings}

    # --- Calculate Summary Statistics ---
    summary_stats = {
        "most_risky_district": {"name": "N/A", "avg": 0},
        "highest_weather": {"name": "N/A", "value": 0},
        "highest_health": {"name": "N/A", "value": 0},
        "highest_disaster": {"name": "N/A", "value": 0},
        "unrated_count": len(KERALA_DISTRICTS) - len(all_ratings)
    }

    if all_ratings:
        for rating in all_ratings:
            # Calculate average risk for finding the most risky district
            avg_risk = (rating.weather_risk + rating.health_risk + rating.disaster_risk) / 3
            if avg_risk > summary_stats["most_risky_district"]["avg"]:
                summary_stats["most_risky_district"]["name"] = rating.district_name
                summary_stats["most_risky_district"]["avg"] = avg_risk
            
            # Check for highest individual risks
            if rating.weather_risk > summary_stats["highest_weather"]["value"]:
                summary_stats["highest_weather"]["name"] = rating.district_name
                summary_stats["highest_weather"]["value"] = rating.weather_risk
            
            if rating.health_risk > summary_stats["highest_health"]["value"]:
                summary_stats["highest_health"]["name"] = rating.district_name
                summary_stats["highest_health"]["value"] = rating.health_risk
                
            if rating.disaster_risk > summary_stats["highest_disaster"]["value"]:
                summary_stats["highest_disaster"]["name"] = rating.district_name
                summary_stats["highest_disaster"]["value"] = rating.disaster_risk

    return render_template('admin/monitor.html', 
                           all_districts=KERALA_DISTRICTS,
                           ratings=ratings_dict,
                           summary=summary_stats, # Pass the new stats to the template
                           active_page='monitor')

@admin_bp.route('/update-district-safety-rating/<string:district_name>', methods=['POST'])
def update_district_safety_rating(district_name):
    """Updates the safety rating for a specific district."""
    try:
        rating = SafetyRating.query.filter_by(district_name=district_name).first()
        if not rating:
            rating = SafetyRating(district_name=district_name)
            db.session.add(rating)

        rating.weather_risk = int(request.form.get('weather_risk'))
        rating.health_risk = int(request.form.get('health_risk'))
        rating.disaster_risk = int(request.form.get('disaster_risk'))
            
        db.session.commit()
        flash(f'Successfully updated safety rating for {district_name}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating safety rating for {district_name}: {str(e)}', 'danger')

    return redirect(url_for('admin.monitor'))
# ### END: UPDATED SAFETY MONITOR LOGIC ###


# ... (User Management routes are unchanged) ...
@admin_bp.route('/manage_users')
def manage_users():
    users = User.query.filter_by(role='user').all()
    return render_template('admin/manage_users.html', users=users, active_page='users')

@admin_bp.route('/api/update-user/<int:user_id>', methods=['PUT'])
def api_update_user(user_id):
    user_to_update = User.query.get_or_404(user_id)
    data = request.get_json()
    user_to_update.Username, user_to_update.Email = data['username'], data['email']
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    return redirect(url_for('admin.manage_users'))