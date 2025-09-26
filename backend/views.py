# backend/views.py

from flask import render_template, flash, jsonify, request
from . import views_bp
from models import db, Destination, SafetyRating
from sqlalchemy import func
from sqlalchemy.orm import joinedload

@views_bp.route('/')
def landing():
    return render_template('landing.html')

@views_bp.route('/dashboard')
def dashboard():
    try:
        districts_query = db.session.query(Destination.Name).distinct().order_by(Destination.Name).all()
        districts = [d[0] for d in districts_query]
        types_query = db.session.query(Destination.Type).distinct().all()
        interests = [t[0] for t in types_query if t[0] is not None]
    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
        districts, interests = [], []
        flash("Could not load dashboard data from the database.", "danger")
    return render_template('user/user_dashboard.html', 
                           districts=districts, 
                           interests=interests,
                           active_page='dashboard')

@views_bp.route('/search')
def search():
    """
    Renders the dedicated search page, displaying all destinations.
    The logic is now corrected to handle the refactored SafetyRating model.
    """
    try:
        # This is a placeholder for a more complex join if needed,
        # but for now, we will fetch separately and combine in Python.
        destinations = Destination.query.order_by(Destination.Name, Destination.Place).all()
    except Exception as e:
        print(f"Error fetching destinations for search page: {e}")
        destinations = []
        flash("Could not load destination data from the database.", "danger")
    
    return render_template('user/search.html', 
                           destinations=destinations, 
                           active_page='search')


@views_bp.route('/api/search-destinations')
def api_search_destinations():
    """
    FIX: This API endpoint now correctly fetches district-based safety ratings
    and applies them to the destination results without a direct DB join.
    """
    query = request.args.get('q', '', type=str)
    
    # 1. Fetch all district ratings into a dictionary for efficient lookup
    all_ratings = SafetyRating.query.all()
    ratings_dict = {r.district_name: r for r in all_ratings}

    # 2. Query destinations based on the search term
    base_query = Destination.query
    if query:
        search_term = f"%{query}%"
        search_results = base_query.filter(
            (Destination.Place.ilike(search_term)) | 
            (Destination.Name.ilike(search_term))
        ).order_by(Destination.Name).all()
    else:
        search_results = base_query.order_by(Destination.Name).all()

    # 3. Build the response list, combining destination data with safety data
    results_list = []
    status_map = {'Very Safe': 'safe', 'Safe': 'safe', 'Moderate': 'caution', 'Risky': 'unsafe'}
    
    for dest in search_results:
        safety_text = 'Not Rated'
        safety_class = 'caution'
        
        rating = ratings_dict.get(dest.Name) # Look up rating by district name
        if rating:
            avg_risk = (rating.weather_risk + rating.health_risk + rating.disaster_risk) / 3
            if avg_risk <= 1.5: safety_text = "Very Safe"
            elif avg_risk <= 2.5: safety_text = "Safe"
            elif avg_risk <= 3.5: safety_text = "Moderate"
            else: safety_text = "Risky"
            safety_class = status_map.get(safety_text, 'caution')

        results_list.append({
            'id': dest.Destination_id,
            'place': dest.Place,
            'name': dest.Name,
            'type': dest.Type.capitalize() if dest.Type else 'N/A',
            'description': dest.Description,
            'budget': dest.budget,
            'image_url': dest.image_url,
            'safety': {
                'text': safety_text,
                'class_name': safety_class
            }
        })

    return jsonify(results_list)


@views_bp.route('/api/increment-search-count/<int:dest_id>', methods=['POST'])
def increment_search_count(dest_id):
    try:
        destination = Destination.query.get(dest_id)
        if destination:
            if destination.search_count is None:
                destination.search_count = 0
            destination.search_count += 1
            db.session.commit()
            return jsonify({'success': True, 'message': 'Count incremented.'})
        return jsonify({'success': False, 'message': 'Destination not found.'}), 404
    except Exception as e:
        db.session.rollback()
        print(f"Error incrementing search count: {e}")
        return jsonify({'success': False, 'message': 'Server error.'}), 500