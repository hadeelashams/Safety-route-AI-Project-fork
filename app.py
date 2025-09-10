from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from db import db  # <-- IMPORT db FROM YOUR NEW db.py FILE
from models import User, Destination, SafetyRating # This import now works perfectly
import os
import datetime
import pandas as pd
from sqlalchemy import func

# (Your existing blueprint imports)
from backend import auth_bp
from backend.login import login_routes
from backend.signup import signup_routes

app = Flask(__name__)

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345678@localhost/saferouteai'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)

db.init_app(app)    


# --- START: CSV Data Loading ---
# Load the risk log data into a pandas DataFrame when the app starts.
# This is more efficient than reading the file on every request.
try:
    # Use more robust CSV reading options to handle formatting issues
    risk_log_df = pd.read_csv('data/risklog.csv', 
                              skipinitialspace=True,
                              quotechar='"',
                              escapechar='\\',
                              on_bad_lines='skip')  # Skip problematic lines
    # Convert event_date column to datetime objects for easier comparison
    if 'date' in risk_log_df.columns:
        risk_log_df['date'] = pd.to_datetime(risk_log_df['date'], errors='coerce')
    print(f"Risk log CSV loaded successfully with {len(risk_log_df)} records.")
except FileNotFoundError:
    print("WARNING: data/risklog.csv not found. Risk analysis will be limited.")
    risk_log_df = pd.DataFrame() # Create an empty DataFrame if file is missing
except Exception as e:
    print(f"WARNING: Error reading data/risklog.csv: {e}. Risk analysis will be limited.")
    risk_log_df = pd.DataFrame() # Create an empty DataFrame if there's a parsing error
# --- END: CSV Data Loading ---


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
    """
    Renders the user dashboard with dynamic data fetched from the database.
    """
    try:
        # ### START: THIS IS THE FIX ###
        # The query now selects from the `Name` column instead of the `Place` column.
        districts_query = db.session.query(Destination.Name).distinct().order_by(Destination.Name).all()
        # ### END: THIS IS THE FIX ###
        
        districts = [d[0] for d in districts_query]

        # Get all unique interest types for the new dropdown
        types_query = db.session.query(Destination.Type).distinct().all()
        interests = [t[0] for t in types_query if t[0] is not None]

        # Get suggested destinations (this logic remains the same)
        suggestions_query = db.session.query(
            Destination, SafetyRating
        ).join(
            SafetyRating, Destination.Destination_id == SafetyRating.destination_id
        ).order_by(func.rand()).limit(3).all() # Use func.rand() for variety

        suggested_destinations = []
        status_map = {'Very Safe': 'safe', 'Safe': 'safe', 'Moderate': 'caution', 'Risky': 'unsafe', 'Unsafe': 'unsafe'}

        for dest, safety in suggestions_query:
            image_filename = f"{dest.Name.lower().replace(' ', '_')}.jpg"
            suggested_destinations.append({
                'name': dest.Name,
                'description': dest.Type.capitalize(),
                'status_text': safety.overall_safety,
                'status_class': status_map.get(safety.overall_safety, 'caution'),
                'image': image_filename
            })
            
    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
        districts, interests, suggested_destinations = [], [], []
        flash("Could not load dashboard data from the database.", "danger")

    return render_template('user_dashboard.html', 
                           districts=districts, 
                           interests=interests,
                           suggested_destinations=suggested_destinations)


# --- START: NEW API ROUTE FOR ROUTE GENERATION ---
@app.route('/api/generate-route', methods=['POST'])
def api_generate_route():
    data = request.get_json()
    source_district = data.get('source')
    dest_district = data.get('destination')
    interest = data.get('interest')

    # --- Simplified Route Generation Logic ---
    # In a real app, this would involve complex graph algorithms (like A* or Dijkstra) and a mapping API.
    # Here, we'll find one potential intermediate stop that matches the interest and is not the source/destination.
    
    potential_stops_query = Destination.query.join(SafetyRating).filter(
        Destination.Type == interest,
        Destination.Place != source_district,
        Destination.Place != dest_district
    ).limit(5).all()

    if not potential_stops_query:
        return jsonify({'success': False, 'message': f'No stops found matching your interest "{interest}". Try another interest.'})

    # --- Safety Analysis using Risk Log ---
    analyzed_stops = []
    status_map = {'Very Safe': 'safe', 'Safe': 'safe', 'Moderate': 'caution', 'Risky': 'unsafe', 'Unsafe': 'unsafe'}
    
    # Define a time window for "recent" events (e.g., last 2 years)
    two_years_ago = datetime.datetime.now() - datetime.timedelta(days=730)

    for stop in potential_stops_query:
        base_safety = stop.safety_ratings[0].overall_safety
        current_safety_text = base_safety
        
        # Check for recent high-impact events from the CSV
        if not risk_log_df.empty:
            recent_risks = risk_log_df[
                (risk_log_df['destination_id'] == stop.Destination_id) &
                (risk_log_df['date'] > two_years_ago)
            ]
            
            if not recent_risks.empty:
                # If there's a recent flood or landslide, downgrade safety
                if any(risk in recent_risks['threat_type'].values for risk in ['Flood', 'Landslide']):
                    current_safety_text = "Unsafe"
                elif 'Disease Outbreak' in recent_risks['threat_type'].values:
                    current_safety_text = "Risky"

        analyzed_stops.append({
            'id': stop.Destination_id,
            'name': stop.Name,
            'type': stop.Type.capitalize(),
            'safety_text': current_safety_text,
            'safety_class': status_map.get(current_safety_text, 'caution')
        })

    # Simple logic: pick the safest stop from our analyzed list
    # Sorting order: 'Safe' > 'Moderate' > 'Risky' > 'Unsafe'
    safety_order = {'Safe': 0, 'Very Safe': 0, 'Moderate': 1, 'Caution': 1, 'Risky': 2, 'Unsafe': 3}
    best_stop = sorted(analyzed_stops, key=lambda x: safety_order.get(x['safety_text'], 99))[0]
    
    # --- Collect Alerts and Tips ---
    alerts = []
    if not risk_log_df.empty:
        stop_alerts = risk_log_df[
            (risk_log_df['destination_id'] == best_stop['id']) &
            (risk_log_df['date'] > two_years_ago)
        ].to_dict('records')
        
        for alert in stop_alerts:
            alerts.append({
                'type': alert['threat_type'],
                'description': alert['description'],
                'date': alert['date'].strftime('%d %B %Y'),
                'severity_class': 'flood-alert-card' if 'Flood' in alert['threat_type'] else 'weather-alert-card'
            })
            
    # --- Final Route Construction ---
    final_route = {
        'source': source_district,
        'destination': dest_district,
        'interest': interest.capitalize(),
        'overall_safety_text': 'Safe with Caution' if best_stop['safety_class'] != 'safe' else 'Mostly Safe',
        'overall_safety_class': 'caution' if best_stop['safety_class'] != 'safe' else 'safe',
        'stops': [best_stop],
        'alerts': alerts,
        'tip': f"While visiting {best_stop['name']}, be mindful of local advisories, especially during monsoon season."
    }

    return jsonify({'success': True, 'route': final_route})

# --- END: NEW API ROUTE ---

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
    """Handles creating a new destination from the modal's JSON data."""
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'success': False, 'message': 'District is a required field'}), 400
        
        selected_district = data.get('name')

        new_dest = Destination(
            Name=selected_district,
            Place=selected_district,
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
    users = User.query.filter_by(role='User').all()
    return render_template('manage_users.html', users=users, active_page='users')

@app.route('/admin/api/update-user/<int:user_id>', methods=['PUT'])
def api_update_user(user_id):
    """Handles updating a user's details from the modal's JSON data."""
    try:
        user_to_update = User.query.get_or_404(user_id)
        data = request.get_json()

        if not data or not data.get('username') or not data.get('email'):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        new_username = data.get('username')
        new_email = data.get('email')

        existing_user = User.query.filter(User.User_id != user_id, User.Username == new_username).first()
        if existing_user:
            return jsonify({'success': False, 'message': f'Username "{new_username}" is already taken.'}), 409

        existing_email = User.query.filter(User.User_id != user_id, User.Email == new_email).first()
        if existing_email:
            return jsonify({'success': False, 'message': f'Email "{new_email}" is already registered.'}), 409

        user_to_update.Username = new_username
        user_to_update.Email = new_email
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'User updated successfully!'})
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