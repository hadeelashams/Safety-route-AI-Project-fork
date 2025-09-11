# backend/aiservice.py

from flask import Blueprint, jsonify, request
from models import db, Destination, SafetyRating
import pandas as pd
import datetime

# --- Blueprint Definition ---
ai_bp = Blueprint('ai_service', __name__)

# --- AI Service Constants & Data Loading ---

# This list defines the geographical order of districts from South to North.
# This is our "map" to determine the path.
KERALA_DISTRICTS_ORDER = [
    "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha", "Kottayam",
    "Idukki", "Ernakulam", "Thrissur", "Palakkad", "Malappuram",
    "Kozhikode", "Wayanad", "Kannur", "Kasaragod"
]

# Load the risk log data into a pandas DataFrame when the blueprint is loaded.
try:
    # ### FIX: Corrected the path to point inside the static directory. ###
    # Assuming the file is named 'risklog.csv' inside the 'data' folder.
    csv_path = 'static/data/risklog.csv'
    risk_log_df = pd.read_csv(csv_path, skipinitialspace=True, on_bad_lines='skip')
    
    if 'date' in risk_log_df.columns:
        risk_log_df['date'] = pd.to_datetime(risk_log_df['date'], errors='coerce')
    print("AI Service: Risk log CSV loaded successfully.")
except FileNotFoundError:
    # ### FIX: Updated the warning message to reflect the correct path. ###
    print(f"AI Service WARNING: {csv_path} not found. Risk analysis will be limited.")
    risk_log_df = pd.DataFrame()
except Exception as e:
    print(f"AI Service WARNING: Error reading {csv_path}: {e}. Risk analysis will be limited.")
    risk_log_df = pd.DataFrame()


# --- API Route ---

@ai_bp.route('/api/generate-route', methods=['POST'])
def generate_ai_route():
    """
    Generates an intelligent route by identifying districts on the path
    and suggesting the safest, most relevant stops.
    """
    data = request.get_json()
    source_district = data.get('source')
    dest_district = data.get('destination')
    interest = data.get('interest')

    # 1. Determine the travel path (districts between source and destination)
    try:
        source_index = KERALA_DISTRICTS_ORDER.index(source_district)
        dest_index = KERALA_DISTRICTS_ORDER.index(dest_district)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid source or destination district provided.'})

    # Create a slice of the districts on the path
    if source_index < dest_index:
        travel_path_districts = KERALA_DISTRICTS_ORDER[source_index : dest_index + 1]
    else: # Traveling from North to South
        travel_path_districts = list(reversed(KERALA_DISTRICTS_ORDER[dest_index : source_index + 1]))

    # Districts for querying stops (exclude source, include destination)
    districts_for_stops = travel_path_districts[1:]

    # 2. Find potential stops along the path matching the user's interest
    potential_stops_query = Destination.query.join(SafetyRating).filter(
        Destination.Name.in_(districts_for_stops), # The 'Name' column is the district
        Destination.Type == interest
    ).all()

    if not potential_stops_query:
        msg = f'No stops matching your interest "{interest.capitalize()}" were found between {source_district} and {dest_district}.'
        return jsonify({'success': False, 'message': msg})

    # 3. Analyze the safety of each potential stop using the risk log
    analyzed_stops = []
    status_map = {'Very Safe': 'safe', 'Safe': 'safe', 'Moderate': 'caution', 'Risky': 'unsafe', 'Unsafe': 'unsafe'}
    two_years_ago = datetime.datetime.now() - datetime.timedelta(days=730)

    for stop in potential_stops_query:
        base_safety = stop.safety_ratings[0].overall_safety
        current_safety_text = base_safety
        
        if not risk_log_df.empty:
            recent_risks = risk_log_df[
                (risk_log_df['destination_id'] == stop.Destination_id) &
                (risk_log_df['date'] > two_years_ago)
            ]
            if not recent_risks.empty:
                if any(risk in recent_risks['threat_type'].values for risk in ['Flood', 'Landslide']):
                    current_safety_text = "Unsafe"
                elif 'Disease Outbreak' in recent_risks['threat_type'].values:
                    current_safety_text = "Risky"

        analyzed_stops.append({
            'id': stop.Destination_id,
            'name': stop.Place,  # Use 'Place' for the specific location name
            'district': stop.Name,
            'type': stop.Type.capitalize(),
            'safety_text': current_safety_text,
            'safety_class': status_map.get(current_safety_text, 'caution')
        })

    # 4. Select the best stops (up to 3 safest stops)
    safety_order = {'Safe': 0, 'Very Safe': 0, 'Moderate': 1, 'Caution': 1, 'Risky': 2, 'Unsafe': 3}
    sorted_stops = sorted(analyzed_stops, key=lambda x: safety_order.get(x['safety_text'], 99))
    best_stops = sorted_stops[:3] # Get the top 1-3 safest stops

    # 5. Collect Alerts and a dynamic Tip for the selected stops
    alerts = []
    stop_names_for_tip = []
    if not risk_log_df.empty:
        for stop in best_stops:
            stop_names_for_tip.append(stop['name'])
            stop_alerts = risk_log_df[
                (risk_log_df['destination_id'] == stop['id']) &
                (risk_log_df['date'] > two_years_ago)
            ].to_dict('records')
            
            for alert in stop_alerts:
                alerts.append({
                    'type': f"{alert['threat_type']} in {stop['name']}",
                    'description': alert['description'],
                    'date': alert['date'].strftime('%d %B %Y'),
                    'severity_class': 'flood-alert-card' if 'Flood' in alert['threat_type'] else 'weather-alert-card'
                })
    
    tip_locations = ", ".join(stop_names_for_tip)
    tip = f"Enjoy your journey! When travelling through {tip_locations}, always check local news for the latest updates."

    # 6. Final Route Construction for the frontend
    final_route = {
        'source': source_district,
        'destination': dest_district,
        'interest': interest.capitalize(),
        'overall_safety_text': 'Safe with Caution',
        'overall_safety_class': 'caution',
        'stops': best_stops,
        'alerts': alerts,
        'tip': tip
    }

    return jsonify({'success': True, 'route': final_route})