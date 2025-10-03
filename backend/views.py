# backend/views.py

from flask import render_template, flash, jsonify, request, session, redirect, url_for
from functools import wraps
from . import views_bp
from models import db, Destination, SafetyRating, User
from sqlalchemy import func
from sqlalchemy.orm import joinedload

# Decorator to ensure a user is logged in for protected pages
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You must be logged in to view this page.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@views_bp.route('/')
def landing():
    """Renders the public landing page."""
    return render_template('landing.html')

@views_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Renders the main user dashboard.
    Fetches data for the route planning form and the user's favorite IDs
    to correctly display favorite buttons on the generated route.
    """
    try:
        districts_query = db.session.query(Destination.Name).distinct().order_by(Destination.Name).all()
        districts = [d[0] for d in districts_query]
        types_query = db.session.query(Destination.Type).distinct().all()
        interests = [t[0] for t in types_query if t[0] is not None]
        
        # Get the current user's favorite destination IDs
        favorite_ids = set()
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user:
                favorite_ids = {dest.Destination_id for dest in user.favorites}

    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
        districts, interests, favorite_ids = [], [], set()
        flash("Could not load dashboard data from the database.", "danger")
    
    return render_template('user/user_dashboard.html', 
                           districts=districts, 
                           interests=interests,
                           favorite_ids_json=list(favorite_ids),
                           active_page='dashboard')

@views_bp.route('/search')
@login_required
def search():
    """
    Renders the destination search page, passing all destinations and the user's
    current favorites to pre-fill the heart icons.
    """
    try:
        destinations = Destination.query.order_by(Destination.Name, Destination.Place).all()
        
        favorite_ids = set()
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user:
                favorite_ids = {dest.Destination_id for dest in user.favorites}

    except Exception as e:
        print(f"Error fetching destinations for search page: {e}")
        destinations = []
        favorite_ids = set()
        flash("Could not load destination data from the database.", "danger")
    
    return render_template('user/search.html', 
                           destinations=destinations,
                           favorite_ids=favorite_ids,
                           active_page='search')


@views_bp.route('/favorites')
@login_required
def favorites():
    """
    Renders the user's personal favorites page.
    Manually attaches safety ratings to each destination for use in the template modal.
    """
    user = User.query.get(session['user_id'])
    favorite_destinations = user.favorites 
    
    # Fetch all safety ratings into a dictionary for efficient lookup
    all_ratings = SafetyRating.query.all()
    ratings_dict = {r.district_name: r for r in all_ratings}
    
    # Manually attach the safety rating object to each destination so the modal can use it
    for dest in favorite_destinations:
        rating = ratings_dict.get(dest.Name)
        if rating:
            # Wrap in a list to mimic the data structure of other pages for template consistency
            dest.safety_ratings = [rating] 
        else:
            dest.safety_ratings = []

    return render_template('user/favorites.html', 
                           destinations=favorite_destinations, 
                           active_page='favorite')


# --- API Endpoints ---

@views_bp.route('/api/search-destinations')
def api_search_destinations():
    """
    API endpoint for live searching. It fetches district-based safety ratings
    and applies them to the destination results without a direct DB join.
    """
    query = request.args.get('q', '', type=str)
    
    all_ratings = SafetyRating.query.all()
    ratings_dict = {r.district_name: r for r in all_ratings}

    base_query = Destination.query
    if query:
        search_term = f"%{query}%"
        search_results = base_query.filter(
            (Destination.Place.ilike(search_term)) | 
            (Destination.Name.ilike(search_term))
        ).order_by(Destination.Name).all()
    else:
        search_results = base_query.order_by(Destination.Name).all()

    results_list = []
    status_map = {'Very Safe': 'safe', 'Safe': 'safe', 'Moderate': 'caution', 'Risky': 'unsafe'}
    
    for dest in search_results:
        safety_text = 'Not Rated'
        safety_class = 'caution'
        
        rating = ratings_dict.get(dest.Name)
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
    """API endpoint to increment the search count for a destination."""
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


@views_bp.route('/api/favorites/add/<int:dest_id>', methods=['POST'])
@login_required
def add_favorite(dest_id):
    """API endpoint to add a destination to the user's favorites."""
    try:
        user = User.query.get(session['user_id'])
        destination = Destination.query.get_or_404(dest_id)
        if destination not in user.favorites:
            user.favorites.append(destination)
            db.session.commit()
        return jsonify({'success': True, 'message': 'Added to favorites.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@views_bp.route('/api/favorites/remove/<int:dest_id>', methods=['POST'])
@login_required
def remove_favorite(dest_id):
    """API endpoint to remove a destination from the user's favorites."""
    try:
        user = User.query.get(session['user_id'])
        destination = Destination.query.get_or_404(dest_id)
        if destination in user.favorites:
            user.favorites.remove(destination)
            db.session.commit()
        return jsonify({'success': True, 'message': 'Removed from favorites.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500