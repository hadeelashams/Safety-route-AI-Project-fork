# backend/views.py

from flask import render_template, flash
from . import views_bp
from models import db, Destination, SafetyRating
from sqlalchemy import func

@views_bp.route('/')
def landing():
    return render_template('landing.html')

@views_bp.route('/dashboard')
def dashboard():
    """
    Renders the user dashboard with dynamic data fetched from the database.
    """
    try:
        districts_query = db.session.query(Destination.Name).distinct().order_by(Destination.Name).all()
        districts = [d[0] for d in districts_query]

        types_query = db.session.query(Destination.Type).distinct().all()
        interests = [t[0] for t in types_query if t[0] is not None]

        suggestions_query = db.session.query(
            Destination, SafetyRating
        ).join(
            SafetyRating, Destination.Destination_id == SafetyRating.destination_id
        ).order_by(func.rand()).limit(3).all()

        suggested_destinations = []
        status_map = {'Very Safe': 'safe', 'Safe': 'safe', 'Moderate': 'caution', 'Risky': 'unsafe'}

        for dest, safety in suggestions_query:
            image_filename = f"{dest.Name.lower().replace(' ', '_')}.jpg"
            suggested_destinations.append({
                'name': dest.Place,
                'description': f"{dest.Type.capitalize()} in {dest.Name}",
                'status_text': safety.overall_safety,
                'status_class': status_map.get(safety.overall_safety, 'caution'),
                'image': image_filename
            })
            
    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
        districts, interests, suggested_destinations = [], [], []
        flash("Could not load dashboard data from the database.", "danger")

    # ### FIX: Added the 'user/' prefix to the template path ###
    return render_template('user/user_dashboard.html', 
                           districts=districts, 
                           interests=interests,
                           suggested_destinations=suggested_destinations)