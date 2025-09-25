# models.py
from db import db
import datetime

class User(db.Model):
    __tablename__ = 'User_table'
    # ... (User model remains unchanged)
    User_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Username = db.Column(db.String(45), nullable=False)
    name = db.Column(db.String(45), nullable=False)
    Email = db.Column(db.String(45), unique=True, nullable=False)
    Password = db.Column(db.String(45), nullable=False)
    Create_id = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    role = db.Column(db.String(45), nullable=False)

    def __repr__(self):
        return f'<User {self.Username}>'

class Destination(db.Model):
    __tablename__ = 'Destination'

    Destination_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Place = db.Column(db.String(100), nullable=False) 
    Name = db.Column(db.String(20), nullable=False)
    Type = db.Column(db.Enum('beach', 'hill', 'wildlife'), nullable=False)
    Description = db.Column(db.Text, nullable=True)
    Create_id = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now) 
    budget = db.Column(db.Integer, nullable=True)
    search_count = db.Column(db.Integer, nullable=False, default=0)
    
    # ### START: NEW IMAGE URL COLUMN ###
    image_url = db.Column(db.String(255), nullable=True)
    # ### END: NEW IMAGE URL COLUMN ###

    safety_ratings = db.relationship('SafetyRating', backref='destination', lazy=True)

    def __repr__(self):
        return f'<Destination {self.Name}>'

class SafetyRating(db.Model):
    __tablename__ = 'Safety_Rating_table'
    # ... (SafetyRating model remains unchanged)
    safety_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('Destination.Destination_id'), nullable=False)
    weather_risk = db.Column(db.Integer, nullable=True)
    health_risk = db.Column(db.Integer, nullable=True)
    disaster_risk = db.Column(db.Integer, nullable=True)
    overall_safety = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f'<SafetyRating Dest:{self.destination_id} Safety:{self.overall_safety}>'