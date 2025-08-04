from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import get_user_by_username

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username_or_email = request.form['email']
        password = request.form['password']
        user = get_user_by_username(username_or_email)
        if user and user['password'] == password:  # Replace with hashed password check later
            session['user_id'] = user['id']
            return redirect(url_for('home'))
        else:
            error = 'Invalid username/email or password'
    return render_template('login.html', error=error)

if __name__ == '__main__':
    app.run(debug=True)
