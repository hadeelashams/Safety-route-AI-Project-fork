# backend/aiservice.py

from flask import Blueprint, jsonify, request, current_app
from models import db, Destination, SafetyRating
import pandas as pd
import datetime
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
    print(f"AI Service WARNING: Could not read {csv_path}: {e}. Recent risk analysis will be limited.")
    risk_log_df = pd.DataFrame()


@ai_bp.route('/api/generate-route', methods=['POST'])
def generate_ai_route():
    data = request.get_json()
    source_district, dest_district = data.get('source'), data.get('destination')
    interest, budget_str = data.get('interest'), data.get('budget')

    try:
        source_index = KERALA_DISTRICTS_ORDER.index(source_district)
        dest_index = KERALA_DISTRICTS_ORDER.index(dest_district)
        user_budget = int(budget_str)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid source, destination, or budget provided.'}), 400

    # Determine the path of districts for the journey
    if source_index < dest_index:
        travel_path_districts = KERALA_DISTRICTS_ORDER[source_index : dest_index + 1]
    else:
        travel_path_districts = list(reversed(KERALA_DISTRICTS_ORDER[dest_index : source_index + 1]))

    districts_for_stops = travel_path_districts[1:] # Exclude the source district for stops

    # 1. Fetch all district ratings into a dictionary for quick lookup
    all_ratings = SafetyRating.query.all()
    district_ratings = {r.district_name: r for r in all_ratings}

    # 2. Query potential destinations based on path, interest, and budget
    potential_stops = Destination.query.filter(
        Destination.Name.in_(districts_for_stops),
        Destination.Type == interest,
        Destination.budget <= user_budget
    ).all()

    if not potential_stops:
        msg = f'No stops matching your interest "{interest.capitalize()}" and budget (under ₹{user_budget:,}) were found between {source_district} and {dest_district}.'
        return jsonify({'success': False, 'message': msg})

    # 3. Analyze stops by looking up their district's rating and deriving overall safety
    analyzed_stops = []
    status_map = {'Very Safe': 'safe', 'Safe': 'safe', 'Moderate': 'caution', 'Risky': 'unsafe'}

    for stop in potential_stops:
        rating = district_ratings.get(stop.Name)
        
        if rating:
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

    # 4. Select the best stops based on safety
    safety_order = {'Very Safe': 0, 'Safe': 1, 'Moderate': 2, 'Risky': 3}
    sorted_stops = sorted(analyzed_stops, key=lambda x: safety_order.get(x['safety_text'], 99))
    best_stops = sorted_stops[:3]

    # 5. Collect recent alerts for the selected stops from the CSV
    alerts, stop_names_for_tip = [], []
    if not risk_log_df.empty:
        two_years_ago = datetime.datetime.now() - datetime.timedelta(days=730)
        for stop in best_stops:
            stop_names_for_tip.append(stop['name'])
            # Assuming 'destination_id' in CSV corresponds to Destination.Destination_id
            stop_alerts = risk_log_df[(risk_log_df['destination_id'] == stop['id']) & (risk_log_df['date'] > two_years_ago)].to_dict('records')
            for alert in stop_alerts:
                alerts.append({
                    'type': f"{alert.get('threat_type', 'Alert')} in {stop['name']}",
                    'description': alert.get('description', 'No details.'),
                    'date': alert['date'].strftime('%d %B %Y') if pd.notna(alert.get('date')) else 'N/A',
                    'severity_class': 'weather-alert-card' # Or derive from data
                })
    
    # 6. Generate a helpful tip
    tip_locations = ", ".join(stop_names_for_tip) if stop_names_for_tip else "your destinations"
    tip = f"Enjoy your journey! When travelling through {tip_locations}, always check local news for the latest updates on weather and road conditions."

    # 7. Determine overall route safety
    overall_safety_text = "Safe"
    if any(s['safety_class'] == 'unsafe' for s in best_stops): overall_safety_text = "Risky"
    elif any(s['safety_class'] == 'caution' for s in best_stops): overall_safety_text = "Moderate"

    # 8. Construct the final route object
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
        # FIX: Changed to a valid and standard model name
        model = genai.GenerativeModel('gemini-flash-lite-latest')
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
        print(f"Gemini API Error: {e}")
        return jsonify({'success': False, 'error': "Sorry, I'm having trouble connecting to the AI assistant right now."}), 500