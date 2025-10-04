# backend/admin.py

from flask import render_template, redirect, url_for, request, jsonify, flash
from . import admin_bp
from models import db, User, Destination # Removed SafetyRating import
import pandas as pd
from backend.auth import admin_required

# --- Constants ---
KERALA_DISTRICTS = sorted([
    "Alappuzha", "Ernakulam", "Idukki", "Kannur", "Kasaragod", "Kollam",
    "Kottayam", "Kozhikode", "Malappuram", "Palakkad", "Pathanamthitta",
    "Thiruvananthapuram", "Thrissur", "Wayanad"
])
RISKLOG_PATH = 'static/data/risklog.csv'

# --- Core Admin Routes ---
@admin_bp.route('/')
@admin_required
def base():
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_users = User.query.filter_by(role='user').count()
    total_destinations = Destination.query.count()
    top_search_name = "N/A"
    try:
        top_destination = Destination.query.filter(Destination.search_count > 0).order_by(Destination.search_count.desc()).first()
        if top_destination:
            top_search_name = top_destination.Place
    except Exception as e:
        print(f"Admin Dashboard WARNING: Could not calculate top location. Error: {e}")
        
    return render_template('admin/admin_dashboard.html', 
                           total_users=total_users, total_destinations=total_destinations, 
                           top_search_name=top_search_name, active_page='dashboard')

# --- Destination Management Routes ---
@admin_bp.route('/manage_destination')
@admin_required
def manage_destination():
    destinations = Destination.query.order_by(Destination.Name).all()
    return render_template('admin/manage_destination.html', 
                           destinations=destinations, all_districts=KERALA_DISTRICTS, 
                           active_page='destinations')

@admin_bp.route('/add-destination', methods=['POST'])
@admin_required
def add_destination():
    try:
        data = request.get_json()
        if not all(k in data for k in ['name', 'place', 'type', 'description', 'budget']):
            return jsonify({'success': False, 'message': 'Missing required fields.'}), 400
        new_dest = Destination(
            Name=data.get('name'), Place=data.get('place'), Type=data.get('type'), 
            Description=data.get('description'), budget=data.get('budget'), image_url=data.get('image_url')
        )
        db.session.add(new_dest)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Destination added successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500

@admin_bp.route('/update-destination/<int:dest_id>', methods=['PUT'])
@admin_required
def update_destination(dest_id):
    try:
        dest = Destination.query.get(dest_id)
        if not dest: return jsonify({'success': False, 'message': 'Destination not found'}), 404
        data = request.get_json()
        dest.Name = data.get('name', dest.Name)
        dest.Place = data.get('place', dest.Place)
        dest.Type = data.get('type', dest.Type)
        dest.Description = data.get('description', dest.Description)
        dest.budget = data.get('budget', dest.budget)
        dest.image_url = data.get('image_url', dest.image_url)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Destination updated successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500

@admin_bp.route('/delete-destination/<int:dest_id>', methods=['POST'])
@admin_required
def delete_destination(dest_id):
    try:
        dest = Destination.query.get_or_404(dest_id)
        db.session.delete(dest)
        db.session.commit()
        flash('Destination deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting destination: {str(e)}', 'danger')
    return redirect(url_for('admin.manage_destination'))

# --- Risk Log CSV Manager Routes (Formerly Safety Monitor) ---
@admin_bp.route('/monitor')
@admin_required
def monitor():
    try:
        df = pd.read_csv(RISKLOG_PATH, skipinitialspace=True)
        df.reset_index(inplace=True)
        risk_log_data = df.to_dict(orient='records')
    except FileNotFoundError:
        flash('risklog.csv not found. You can add the first entry to create it.', 'warning')
        risk_log_data = []
    except Exception as e:
        flash(f'Error reading risk log file: {e}', 'danger')
        risk_log_data = []
        
    return render_template('admin/monitor.html', 
                           risk_log_data=risk_log_data,
                           all_districts=KERALA_DISTRICTS,
                           active_page='monitor')

@admin_bp.route('/add-risk-log-row', methods=['POST'])
@admin_required
def add_risk_log_row():
    try:
        new_data = {
            'date': [request.form['date']], 'district': [request.form['district']], 'place': [request.form['place']],
            'temperature_c': [float(request.form['temperature_c'])], 'rainfall_mm': [float(request.form['rainfall_mm'])],
            'humidity_percent': [int(request.form['humidity_percent'])], 'disease_cases': [int(request.form['disease_cases'])],
            'disaster_event': [request.form['disaster_event']], 'description': [request.form['description']]
        }
        new_row_df = pd.DataFrame(new_data)
        try:
            df = pd.read_csv(RISKLOG_PATH)
            df = pd.concat([df, new_row_df], ignore_index=True)
        except FileNotFoundError:
            df = new_row_df
        df.to_csv(RISKLOG_PATH, index=False)
        flash('New risk log entry added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding entry: {e}', 'danger')
    return redirect(url_for('admin.monitor'))

@admin_bp.route('/update-risk-log-row', methods=['POST'])
@admin_required
def update_risk_log_row():
    try:
        row_index = int(request.form['row_index'])
        df = pd.read_csv(RISKLOG_PATH)
        if not (0 <= row_index < len(df)):
            flash('Invalid row index for update.', 'danger')
            return redirect(url_for('admin.monitor'))
        df.loc[row_index, 'date'] = request.form['date']
        df.loc[row_index, 'district'] = request.form['district']
        df.loc[row_index, 'place'] = request.form['place']
        df.loc[row_index, 'temperature_c'] = float(request.form['temperature_c'])
        df.loc[row_index, 'rainfall_mm'] = float(request.form['rainfall_mm'])
        df.loc[row_index, 'humidity_percent'] = int(request.form['humidity_percent'])
        df.loc[row_index, 'disease_cases'] = int(request.form['disease_cases'])
        df.loc[row_index, 'disaster_event'] = request.form['disaster_event']
        df.loc[row_index, 'description'] = request.form['description']
        df.to_csv(RISKLOG_PATH, index=False)
        flash(f'Row {row_index} updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating row: {e}', 'danger')
    return redirect(url_for('admin.monitor'))

@admin_bp.route('/delete-risk-log-row/<int:row_index>', methods=['POST'])
@admin_required
def delete_risk_log_row(row_index):
    try:
        df = pd.read_csv(RISKLOG_PATH)
        df = df.drop(index=row_index).reset_index(drop=True)
        df.to_csv(RISKLOG_PATH, index=False)
        flash(f'Row {row_index} deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting row: {e}', 'danger')
    return redirect(url_for('admin.monitor'))

# --- Safety Analysis Visualization Route ---
@admin_bp.route('/safety-analysis')
@admin_required
def safety_analysis():
    safety_data = []
    try:
        df = pd.read_csv(RISKLOG_PATH, skipinitialspace=True)
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
        df = df.where(pd.notnull(df), None)
        safety_data = df.to_dict(orient='records')
    except FileNotFoundError:
        flash('risklog.csv not found. Safety analysis data is unavailable.', 'warning')
    except Exception as e:
        flash(f'An error occurred while reading safety data: {str(e)}', 'danger')
    return render_template('admin/safety.html', 
                           safety_data=safety_data,
                           active_page='safety_analysis')

# --- User Management Routes ---
@admin_bp.route('/manage_users')
@admin_required
def manage_users():
    users = User.query.filter_by(role='user').all()
    return render_template('admin/manage_users.html', users=users, active_page='users')

@admin_bp.route('/api/update-user/<int:user_id>', methods=['PUT'])
@admin_required
def api_update_user(user_id):
    try:
        user_to_update = User.query.get_or_404(user_id)
        data = request.get_json()
        if 'username' in data:
            existing_user = User.query.filter(User.Username == data['username'], User.User_id != user_id).first()
            if existing_user: return jsonify({'success': False, 'message': 'Username already taken.'}), 400
            user_to_update.Username = data['username']
        if 'email' in data:
            existing_email = User.query.filter(User.Email == data['email'], User.User_id != user_id).first()
            if existing_email: return jsonify({'success': False, 'message': 'Email already in use.'}), 400
            user_to_update.Email = data['email']
        db.session.commit()
        return jsonify({'success': True, 'message': 'User updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin.manage_users'))