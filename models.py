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
    search_count = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(255), nullable=True)

    @property
    def safety_ratings(self):
        """
        Dynamic property that returns safety rating data calculated from CSV.
        This maintains compatibility with templates expecting safety_ratings[0].overall_safety.
        """
        try:
            # Import here to avoid circular imports
            from backend.aiservice import calculate_safety_from_csv
            safety_info = calculate_safety_from_csv(self.Name, self.Place)
            
            # Return a list with a single mock safety rating object for template compatibility
            class MockSafetyRating:
                def __init__(self, overall_safety):
                    self.overall_safety = overall_safety
            
            return [MockSafetyRating(safety_info['text'])]
        except Exception as e:
            print(f"Error calculating safety for {self.Name}, {self.Place}: {e}")
            # Return default safety rating if calculation fails
            class MockSafetyRating:
                def __init__(self, overall_safety):
                    self.overall_safety = overall_safety
            return [MockSafetyRating('Moderate')]

    def __repr__(self):
        return f'<Destination {self.Name}>'