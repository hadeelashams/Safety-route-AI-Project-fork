# models.py
from db import db
import datetime

# NEW: Association table for the many-to-many relationship between users and favorites
user_favorites = db.Table('user_favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('User_table.User_id'), primary_key=True),
    db.Column('destination_id', db.Integer, db.ForeignKey('Destination.Destination_id'), primary_key=True)
)


class User(db.Model):
    __tablename__ = 'User_table'
    User_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Username = db.Column(db.String(45), nullable=False)
    name = db.Column(db.String(45), nullable=False)
    Email = db.Column(db.String(45), unique=True, nullable=False)
    Password = db.Column(db.String(45), nullable=False)
    Create_id = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    role = db.Column(db.String(45), nullable=False)

    # ADDED: Relationship to favorite destinations
    favorites = db.relationship('Destination', secondary=user_favorites, lazy='subquery',
                                backref=db.backref('favorited_by', lazy=True))

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