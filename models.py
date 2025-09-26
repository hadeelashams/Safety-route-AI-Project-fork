# models.py
from db import db
import datetime

class User(db.Model):
    __tablename__ = 'User_table'
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
    Name = db.Column(db.String(20), nullable=False) # This is the District Name
    Type = db.Column(db.Enum('beach', 'hill', 'wildlife'), nullable=False)
    Description = db.Column(db.Text, nullable=True)
    Create_id = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now) 
    budget = db.Column(db.Integer, nullable=True)
    
    # ### MODIFIED/ADDED COLUMNS ###
    search_count = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(255), nullable=True)


    def __repr__(self):
        return f'<Destination {self.Name}>'

# This model now represents a district's safety rating.
class SafetyRating(db.Model):
    __tablename__ = 'safety_rating_table'

    safety_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # This column stores the name of the district (e.g., "Ernakulam")
    district_name = db.Column(db.String(50), unique=True, nullable=False)
    
    weather_risk = db.Column(db.Integer, nullable=False, default=1)
    health_risk = db.Column(db.Integer, nullable=False, default=1)
    disaster_risk = db.Column(db.Integer, nullable=False, default=1)
    
    # The `overall_safety` column is removed as it will be calculated dynamically.

    def __repr__(self):
        return f'<SafetyRating for {self.district_name}>'