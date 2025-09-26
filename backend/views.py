# backend/views.py

# ... (imports and other routes up to api_search_destinations are unchanged) ...
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
    """
    try:
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
    query = request.args.get('q', '', type=str)
    
    base_query = Destination.query.options(
        joinedload(Destination.safety_ratings, innerjoin=False)
    )

    if query:
        search_term = f"%{query}%"
        search_results = base_query.filter(Destination.Place.ilike(search_term)).order_by(Destination.Name).all()
    else:
        search_results = base_query.order_by(Destination.Name).all()

    results_list = []
    status_map = {'Very Safe': 'safe', 'Safe': 'safe', 'Moderate': 'caution', 'Risky': 'unsafe'}
    for dest in search_results:
        safety_text = 'Not Rated'
        safety_class = 'caution'
        if dest.safety_ratings:
            if dest.safety_ratings[0].overall_safety:
                safety_text = dest.safety_ratings[0].overall_safety
                safety_class = status_map.get(safety_text, 'caution')

        results_list.append({
            'id': dest.Destination_id,
            'place': dest.Place,
            'name': dest.Name,
            'type': dest.Type.capitalize(),
            'description': dest.Description,
            'budget': dest.budget,
            'image_url': dest.image_url, # <-- ADDED
            'safety': {
                'text': safety_text,
                'class_name': safety_class
            }
        })

    return jsonify(results_list)

# ... (increment_search_count is unchanged) ...
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