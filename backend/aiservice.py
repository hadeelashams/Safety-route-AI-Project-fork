# backend/aiservice.py

from flask import Blueprint, jsonify, request, current_app
from models import db, Destination # SafetyRating model is no longer needed
import pandas as pd
import datetime
import google.generativeai as genai

ai_bp = Blueprint('ai_service', __name__)

# --- Centralized AI Model Configuration ---
_gemini_model = None
GEMINI_MODEL_NAME = 'gemini-flash-lite-latest'

def _get_gemini_model():
    """Initializes and returns a singleton instance of the Gemini generative model."""
    global _gemini_model
    if _gemini_model:
        return _gemini_model
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key:
        print("AI Service WARNING: GEMINI_API_KEY not configured.")
        return None
    try:
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        return _gemini_model
    except Exception as e:
        print(f"AI Service ERROR: Failed to initialize Gemini model: {e}")
        return None

# --- Helper Functions ---
def _build_travel_tip(stop_names: list[str] | None) -> str:
    """Return a short travel tip string for the given stop names."""
    tip_locations = ", ".join(stop_names) if stop_names else "your destinations"
    return f"Enjoy your journey! When travelling through {tip_locations}, always check local news for the latest updates on weather and road conditions."

# --- Data Loading ---
KERALA_DISTRICTS_ORDER = [
    "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha", "Kottayam",
    "Idukki", "Ernakulam", "Thrissur", "Palakkad", "Malappuram",
    "Kozhikode", "Wayanad", "Kannur", "Kasaragod"
]
try:
    csv_path = 'static/data/risklog.csv'
    risk_log_df = pd.read_csv(csv_path, skipinitialspace=True, on_bad_lines='skip')
    risk_log_df.columns = [c.strip().lower().replace(' ', '_') for c in risk_log_df.columns]
    if 'date' in risk_log_df.columns:
        risk_log_df['date'] = pd.to_datetime(risk_log_df['date'], errors='coerce')
    print("AI Service: Risk log CSV loaded successfully.")
except Exception as e:
    print(f"AI Service WARNING: Could not read {csv_path}: {e}. Risk analysis will be limited.")
    risk_log_df = pd.DataFrame()

# --- Centralized Safety Calculation Function ---
def calculate_safety_from_csv(district_name, place_name=None):
    """
    Calculates a safety score and text based on historical data from risklog.csv.
    This function is the single source of truth for safety assessments.
    """
    status_map = {'Very Safe': 'safe', 'Safe': 'safe', 'Moderate': 'caution', 'Risky': 'unsafe'}
    
    if risk_log_df.empty:
        return {'text': 'Moderate', 'class': 'caution'}

    two_years_ago = datetime.datetime.now() - datetime.timedelta(days=730)
    
    mask = (risk_log_df['district'].str.lower() == district_name.lower()) & (risk_log_df['date'] > two_years_ago)
    if place_name:
        mask &= (risk_log_df['place'].str.lower() == place_name.lower())
        
    relevant_events = risk_log_df[mask]
    
    if relevant_events.empty:
        return {'text': 'Very Safe', 'class': 'safe'}

    risk_score = 0
    risk_score += (relevant_events['disaster_event'].str.lower() != 'none').sum() * 5
    risk_score += relevant_events['disease_cases'].sum() * 0.5
    risk_score += (relevant_events['temperature_c'] > 35).sum() * 1
    risk_score += (relevant_events['rainfall_mm'] > 100).sum() * 2

    if risk_score == 0: safety_text = "Very Safe"
    elif risk_score <= 5: safety_text = "Safe"
    elif risk_score <= 15: safety_text = "Moderate"
    else: safety_text = "Risky"
        
    return {'text': safety_text, 'class': status_map.get(safety_text, 'caution')}


# --- API Endpoints ---
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

    if source_index < dest_index:
        travel_path_districts = KERALA_DISTRICTS_ORDER[source_index : dest_index + 1]
    else:
        travel_path_districts = list(reversed(KERALA_DISTRICTS_ORDER[dest_index : source_index + 1]))
    districts_for_stops = travel_path_districts[1:]
    
    potential_stops = Destination.query.filter(
        Destination.Name.in_(districts_for_stops),
        Destination.Type == interest,
        Destination.budget <= user_budget
    ).all()

    if not potential_stops:
        msg = f'No stops matching your interest "{interest.capitalize()}" and budget (under ₹{user_budget:,}) were found between {source_district} and {dest_district}.'
        return jsonify({'success': False, 'message': msg})

    analyzed_stops = []
    for stop in potential_stops:
        safety_info = calculate_safety_from_csv(stop.Name, stop.Place)
        analyzed_stops.append({
            'id': stop.Destination_id, 'name': stop.Place, 'district': stop.Name,
            'type': stop.Type.capitalize(), 'budget': stop.budget,
            'safety_text': safety_info['text'], 'safety_class': safety_info['class']
        })

    safety_order = {'Very Safe': 0, 'Safe': 1, 'Moderate': 2, 'Risky': 3}
    sorted_stops = sorted(analyzed_stops, key=lambda x: safety_order.get(x['safety_text'], 99))
    best_stops = sorted_stops[:3]

    alerts, stop_names_for_tip = [], []
    if not risk_log_df.empty:
        two_years_ago = datetime.datetime.now() - datetime.timedelta(days=730)
        severity_map = {'landslide': 'alert-high', 'flood': 'alert-high', 'cyclone': 'alert-high', 'heatwave': 'alert-medium', 'drought': 'alert-medium'}
        for stop in best_stops:
            stop_names_for_tip.append(stop['name'])
            mask = ((risk_log_df['place'].str.lower() == stop['name'].lower()) & (risk_log_df['district'].str.lower() == stop['district'].lower()) & (risk_log_df['date'] > two_years_ago))
            for _, alert_row in risk_log_df[mask].iterrows():
                event_type = alert_row.get('disaster_event', 'Alert')
                if str(event_type).lower() == 'none': continue
                severity = severity_map.get(str(event_type).lower(), 'alert-low')
                alerts.append({
                    'type': f"{str(event_type).capitalize()} in {stop['name']}",
                    'description': alert_row.get('description', 'No details available.'),
                    'date': alert_row['date'].strftime('%d %B %Y') if pd.notna(alert_row.get('date')) else 'N/A',
                    'severity_class': severity 
                })

    tip = _build_travel_tip(stop_names_for_tip)
    
    overall_safety_text = "Safe"
    if any(s['safety_class'] == 'unsafe' for s in best_stops): overall_safety_text = "Risky"
    elif any(s['safety_class'] == 'caution' for s in best_stops): overall_safety_text = "Moderate"
    status_map = {'Very Safe': 'safe', 'Safe': 'safe', 'Moderate': 'caution', 'Risky': 'unsafe'}

    final_route = {
        'source': source_district, 'destination': dest_district, 'interest': interest.capitalize(),
        'overall_safety_text': overall_safety_text, 'overall_safety_class': status_map.get(overall_safety_text, 'caution'),
        'stops': best_stops, 'alerts': alerts, 'tip': tip
    }
    return jsonify({'success': True, 'route': final_route})

@ai_bp.route('/api/chat', methods=['POST'])
def chat_with_gemini():
    user_message = (request.get_json() or {}).get('message')
    if not user_message: return jsonify({'success': False, 'error': 'No message provided.'}), 400
    model = _get_gemini_model()
    if not model: return jsonify({'success': False, 'error': 'AI assistant is not configured.'}), 500
    try:
        prompt = f"""
        You are a friendly travel assistant for Kerala, India. Provide safe and useful advice.
        Format answers using Markdown (lists, bold text, etc.).
        User question: "{user_message}"
        """
        response = model.generate_content(prompt)
        return jsonify({'success': True, 'reply': response.text})
    except Exception as e:
        return jsonify({'success': False, 'error': "AI assistant connection error."}), 500

@ai_bp.route('/api/tip', methods=['POST', 'GET'])
def get_travel_tip():
    stops = (request.get_json(silent=True) or {}).get('stops') if request.method == 'POST' else None
    model = _get_gemini_model()
    if not model:
        return jsonify({'success': True, 'tip': _build_travel_tip(stops), 'source': 'fallback'})
    try:
        locations_text = ", ".join(str(x) for x in stops) if stops else "your destinations"
        prompt = f"""
        Create a short, friendly, practical travel safety tip for a trip in Kerala through {locations_text}.
        Include a 1-2 sentence summary, up to 3 short bullet points, and a packing/precaution sentence.
        Return plain text only, no markdown.
        """
        response = model.generate_content(prompt)
        generated_tip = response.text.strip() if response.text else _build_travel_tip(stops)
        return jsonify({'success': True, 'tip': generated_tip, 'source': 'gemini'})
    except Exception as e:
        return jsonify({'success': True, 'tip': _build_travel_tip(stops), 'source': 'fallback', 'warning': 'AI generation failed.'})