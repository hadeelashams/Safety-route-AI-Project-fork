import mysql.connector
import hashlib

# MySQL configuration (moved from app.py)
db_config = {
    'user': 'root',
    'password': '12345678',
    'host': 'localhost',
    'database': 'saferouteai'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def create_user(username, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "INSERT INTO users (username, password) VALUES (%s, %s)"
    cursor.execute(query, (username, hashed_pw))
    conn.commit()
    cursor.close()
    conn.close()

def get_user_by_username(username_or_email):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM users WHERE username = %s OR email = %s"
    cursor.execute(query, (username_or_email, username_or_email))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user
