# backend/auth.py

from flask import render_template, request, redirect, url_for, flash, session
from functools import wraps # <-- ADDED THIS IMPORT
from . import auth_bp
from models import User
from db import db

# ### START: ADDED DECORATOR ###
def admin_required(f):
    """
    Ensures the user is logged in and has the 'admin' role.
    If not, it flashes a message and redirects to the login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in and has the admin role
        if 'role' not in session or session['role'] != 'admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
# ### END: ADDED DECORATOR ###


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['fullname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form.get('role', 'user')

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('signup.html')

        existing_user = User.query.filter((User.Username == username) | (User.Email == email)).first()
        if existing_user:
            flash("Username or email already exists.", "danger")
            return render_template('signup.html')

        # --- REVERTED TO PLAINTEXT ---
        # Password is now stored directly as it was entered.
        new_user = User(
            name=name,
            Email=email,
            Username=username,
            Password=password,  # Storing the plaintext password
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(Username=username).first()

        # --- REVERTED TO PLAINTEXT ---
        # A simple string comparison is used instead of a hash check.
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