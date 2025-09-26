# backend/aiservice.py

from flask import Blueprint, jsonify, request
from models import db, Destination, SafetyRating # <-- Use the refactored SafetyRating model
import pandas as pd
import datetime
from flask import current_app
import google.generativeai as genai

ai_bp = Blueprint('ai_service', __name__)


# --- AI Service Constants & Data Loading ---

KERALA_DISTRICTS_ORDER = [
    "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha", "Kottayam",
    "Idukki", "Ernakulam", "Thrissur", "Palakkad", "Malappuram",
    "Kozhikode", "Wayanad", "Kannur", "Kasaragod"
]

try:
    csv_path = 'static/data/risklog.csv'
    risk_log_df = pd.read_csv(csv_path, skipinitialspace=True, on_bad_lines='skip')
    if 'date' in risk_log_df.columns:
        risk_log_df['date'] = pd.to_datetime(risk_log_df['date'], errors='coerce')
    print("AI Service: Risk log CSV loaded successfully.")

except Exception as e:
    print(f"AI Service WARNING: Could not read {csv_path}: {e}.")
    risk_log_df = pd.DataFrame()


@ai_bp.route('/api/generate-route', methods=['POST'])
def generate_ai_route():
    data = request.get_json()
    source_district, dest_district = data.get('source'), data.get('destination')
    interest, budget_str = data.get('interest'), data.get('budget')

except Exception:
    print(f"AI Service WARNING: risklog.csv not found or unreadable. Risk analysis will be limited.")
    risk_log_df = pd.DataFrame()


# --- API Route ---
@ai_bp.route('/api/generate-route', methods=['POST'])
def generate_ai_route():
    data = request.get_json()
    source_district = data.get('source')
    dest_district = data.get('destination')
    interest = data.get('interest')
    budget_str = data.get('budget')

    try:
        source_index = KERALA_DISTRICTS_ORDER.index(source_district)
        dest_index = KERALA_DISTRICTS_ORDER.index(dest_district)
        user_budget = int(budget_str)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid source, destination, or budget provided.'}), 400

    if source_index < dest_index:
        travel_path_districts = KERALA_DISTRICTS_ORDER[source_index : dest_index + 1]
    else:
        travel_path_districts = list(reversed(KERALA_DISTRICTS_ORDER[dest_index : source_index + 1]))

    
    districts_for_stops = travel_path_districts[1:]

    # 1. Fetch all district ratings into a dictionary for quick lookup
    all_ratings = SafetyRating.query.all()
    district_ratings = {r.district_name: r for r in all_ratings}

    # 2. Query potential destinations
    potential_stops = Destination.query.filter(

    districts_for_stops = travel_path_districts[1:]

    # ### START: THIS IS THE FIX ###
    # We change the query to use an outerjoin. This finds all destinations matching
    # the criteria, even if they don't have a safety rating yet.
    potential_stops_query = Destination.query.outerjoin(SafetyRating).filter(
        Destination.Name.in_(districts_for_stops),
        Destination.Type == interest,
        Destination.budget <= user_budget
    ).all()
    # ### END: THIS IS THE FIX ###

    if not potential_stops:
        msg = f'No stops matching your criteria were found between {source_district} and {dest_district}.'
        return jsonify({'success': False, 'message': msg})

    # 3. Analyze stops by looking up their district's rating and deriving overall safety

    if not potential_stops_query:
        msg = f'No stops matching your interest "{interest.capitalize()}" and budget (under ₹{user_budget:,}) were found between {source_district} and {dest_district}.'
        return jsonify({'success': False, 'message': msg})


    analyzed_stops = []
    status_map = {'Very Safe': 'safe', 'Safe': 'safe', 'Moderate': 'caution', 'Risky': 'unsafe'}

    for stop in potential_stops:
        # Look up the rating using the destination's district name (stop.Name)
        rating = district_ratings.get(stop.Name)
        
        if rating:
            # Derive overall safety on the fly from the rating's risk scores
            avg_risk = (rating.weather_risk + rating.health_risk + rating.disaster_risk) / 3
            if avg_risk <= 1.5: safety_text = "Very Safe"
            elif avg_risk <= 2.5: safety_text = "Safe"
            elif avg_risk <= 3.5: safety_text = "Moderate"
            else: safety_text = "Risky"
        else:
            safety_text = "Moderate" # Default for unrated districts

        analyzed_stops.append({
            'id': stop.Destination_id, 'name': stop.Place, 'district': stop.Name,
            'type': stop.Type.capitalize(), 'budget': stop.budget,
            'safety_text': safety_text, 'safety_class': status_map.get(safety_text, 'caution')
        })

    # 4. Select the best stops
    safety_order = {'Very Safe': 0, 'Safe': 1, 'Moderate': 2, 'Risky': 3}
    sorted_stops = sorted(analyzed_stops, key=lambda x: safety_order.get(x['safety_text'], 99))
    best_stops = sorted_stops[:3]

    # 5. Collect alerts
    alerts, stop_names_for_tip = [], []
    if not risk_log_df.empty:
        two_years_ago = datetime.datetime.now() - datetime.timedelta(days=730)
        for stop in best_stops:
            stop_names_for_tip.append(stop['name'])
            stop_alerts = risk_log_df[(risk_log_df['destination_id'] == stop['id']) & (risk_log_df['date'] > two_years_ago)].to_dict('records')

    for stop in potential_stops_query:
        # Check if a rating exists, otherwise default to "Not Rated"
        base_safety = "Not Rated"
        if stop.safety_ratings:
             base_safety = stop.safety_ratings[0].overall_safety or "Not Rated"

        current_safety_text = base_safety
        
        if not risk_log_df.empty and 'destination_id' in risk_log_df.columns:
            recent_risks = risk_log_df[
                (risk_log_df['destination_id'] == stop.Destination_id) &
                (pd.notna(risk_log_df['date'])) & # Ensure date is not NaT
                (risk_log_df['date'] > two_years_ago)
            ]
            if not recent_risks.empty:
                if any(risk in recent_risks['threat_type'].values for risk in ['Flood', 'Landslide']):
                    current_safety_text = "Unsafe"
                elif 'Disease Outbreak' in recent_risks['threat_type'].values:
                    current_safety_text = "Risky"

        analyzed_stops.append({
            'id': stop.Destination_id,
            'name': stop.Place,
            'district': stop.Name,
            'type': stop.Type.capitalize(),
            'budget': stop.budget,
            'safety_text': current_safety_text,
            'safety_class': status_map.get(current_safety_text, 'caution')
        })

    safety_order = {'Safe': 0, 'Very Safe': 0, 'Moderate': 1, 'Caution': 1, 'Not Rated': 1, 'Risky': 2, 'Unsafe': 3}
    sorted_stops = sorted(analyzed_stops, key=lambda x: safety_order.get(x['safety_text'], 99))
    best_stops = sorted_stops[:3]

    alerts = []
    stop_names_for_tip = []
    if not risk_log_df.empty and 'destination_id' in risk_log_df.columns:
        for stop in best_stops:
            stop_names_for_tip.append(stop['name'])
            stop_alerts = risk_log_df[
                (risk_log_df['destination_id'] == stop['id']) &
                (pd.notna(risk_log_df['date'])) &
                (risk_log_df['date'] > two_years_ago)
            ].to_dict('records')
          
            for alert in stop_alerts:
                alerts.append({'type': f"{alert['threat_type']} in {stop['name']}",'description': alert['description'],'date': alert['date'].strftime('%d %B %Y'),'severity_class': 'weather-alert-card'})
    
    tip_locations = ", ".join(stop_names_for_tip) if stop_names_for_tip else "your destinations"

    tip = f"Enjoy your journey! When travelling through {tip_locations}, always check local news for updates."

    # 6. Final Route Construction
    overall_safety_text = "Safe"
    if any(s['safety_class'] == 'unsafe' for s in best_stops): overall_safety_text = "Risky"
    elif any(s['safety_class'] == 'caution' for s in best_stops): overall_safety_text = "Moderate"

    tip = f"Enjoy your journey! When travelling through {tip_locations}, always check local news for the latest updates."


    final_route = {
        'source': source_district, 'destination': dest_district, 'interest': interest.capitalize(),
        'overall_safety_text': overall_safety_text, 'overall_safety_class': status_map.get(overall_safety_text, 'caution'),
        'stops': best_stops, 'alerts': alerts, 'tip': tip
    }

    return jsonify({'success': True, 'route': final_route})

@ai_bp.route('/api/chat', methods=['POST'])
def chat_with_gemini():
    data = request.get_json()
    user_message = data.get('message')
    if not user_message: return jsonify({'success': False, 'error': 'No message provided.'}), 400
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key: return jsonify({'success': False, 'error': 'API key not configured.'}), 500
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        prompt = f"""
        You are a friendly and helpful travel assistant for Kerala, India. 
        Your goal is to provide safe and useful travel advice.
        Format your answers using Markdown. Use lists, bold text, and headings to make the response clear and easy to read.
        For example, if asked about safe places in Munnar, you could respond with:
        
        "Of course! Here are some famously safe and beautiful spots in Munnar:
        
        *   **Mattupetty Dam:** Known for its serene lake and boating.
        *   **Top Station:** Offers stunning panoramic views.
        *   **Eravikulam National Park:** A great place for wildlife spotting.
        
        Always check the weather before you go, especially during monsoon season!"

        Now, answer the following user question: "{user_message}"
        """
        response = model.generate_content(prompt)
        return jsonify({'success': True, 'reply': response.text})
    except Exception as e:
        return jsonify({'success': False, 'error': "Sorry, I'm having trouble connecting right now."}), 500