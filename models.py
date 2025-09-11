# models.py
from db import db
import datetime

class User(db.Model):
    __tablename__ = 'u' \
    'ser'

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
    # FIX: Changed String(20) to String(100) to match DDL
    Place = db.Column(db.String(100), nullable=False) 
    Name = db.Column(db.String(20), nullable=False)
    Type = db.Column(db.Enum('beach', 'hill', 'wildlife'), nullable=False)
    Description = db.Column(db.Text, nullable=True)
    # NOTE: DDL uses TIMESTAMP, SQLAlchemy's DateTime handles this correctly
    Create_id = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now) 

    # This relationship remains, allowing you to access safety ratings from a destination object
    safety_ratings = db.relationship('SafetyRating', backref='destination', lazy=True)

    def __repr__(self):
        return f'<Destination {self.Name}>'

# ### START: MAJOR CORRECTION FOR SafetyRating MODEL ###
# This class now perfectly matches your `Safety_Rating_table` DDL.
class SafetyRating(db.Model):
    __tablename__ = 'Safety_Rating_table'

    # FIX: Column name changed from Rating_id to safety_id
    safety_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # FIX: Column name changed from Destination_id to destination_id
    # and ForeignKey now points to the correct column in the Destination table
    destination_id = db.Column(db.Integer, db.ForeignKey('Destination.Destination_id'), nullable=False)

    # NEW: Added columns from your DDL
    weather_risk = db.Column(db.Integer, nullable=True)
    health_risk = db.Column(db.Integer, nullable=True)
    disaster_risk = db.Column(db.Integer, nullable=True)

    # This column was correct from the previous fix and matches your DDL
    overall_safety = db.Column(db.String(50), nullable=True)

    # REMOVED: User_id, Rating, Comment, Created_at, and the user relationship,
    # as they do not exist in your DDL for this table.

    def __repr__(self):
        return f'<SafetyRating Dest:{self.destination_id} Safety:{self.overall_safety}>'
# ### END: MAJOR CORRECTION FOR SafetyRating MODEL ###