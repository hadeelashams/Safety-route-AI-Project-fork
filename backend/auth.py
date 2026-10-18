# backend/auth.py

from flask import render_template, request, redirect, url_for, flash, session
from functools import wraps
from . import auth_bp
from models import User
from db import db
# REMOVED: from email_validator import validate_email, EmailNotValidError

def admin_required(f):
    """
    Ensures the user is logged in and has the 'admin' role.
    If not, it flashes a message and redirects to the login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


# ### ADDED: Strong Password Validator ###
def is_strong_password(password):
    """
    Checks if a password meets the strength requirements and returns a descriptive error message.
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    errors = []
    if len(password) < 8:
        errors.append("be at least 8 characters long")
    if not any(c.isupper() for c in password):
        errors.append("contain an uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("contain a lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("contain a number")
    
    special_characters = "!@#$%^&*()-_=+"
    if not any(c in special_characters for c in password):
        errors.append(f"contain a special character (e.g., {special_characters})")
        
    if not errors:
        return True, ""
    
    # Construct a user-friendly message
    message = "Password must " + ", ".join(errors) + "."
    return False, message


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['fullname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form.get('role', 'user')

        # ### START: Simple Email Validation (No Package) ###
        if '@' not in email or '.' not in email.split('@')[-1]:
            flash("Please enter a valid email address.", "danger")
            return render_template('signup.html')
        # ### END: Simple Email Validation ###

        # ### MODIFIED: Strong Password Validation ###
        strong_enough, message = is_strong_password(password)
        if not strong_enough:
            flash(message, "danger")
            return render_template('signup.html')

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('signup.html')

        existing_user = User.query.filter((User.Username == username) | (User.Email == email)).first()
        if existing_user:
            flash("Username or email already exists.", "danger")
            return render_template('signup.html')

        new_user = User(
            name=name,
            Email=email,
            Username=username,
            Password=password,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # ### ADDED: Prevent access if already logged in ###
    if 'user_id' in session:
        flash("You are already logged in.", "info")
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        # Default to user dashboard if role is 'user' or not explicitly admin
        return redirect(url_for('views.dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(Username=username).first()

        if user and user.Password == password:
            session['user_id'] = user.User_id
            session['username'] = user.Username
            session['role'] = user.role
            
            flash('Login successful!', 'success')
            
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'user':
                return redirect(url_for('views.dashboard'))
            else:
                flash('Unknown user role.', 'danger')
                return render_template('login.html')
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('views.landing'))