from db import db
import datetime

class User(db.Model):
    __tablename__ = 'User_table'

    User_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Username = db.Column(db.String(45), nullable=False)
    name = db.Column(db.String(45), nullable=False)
    Email = db.Column(db.String(45), unique=True, nullable=False)
    Password = db.Column(db.String(45), nullable=False)  # plain text (insecure)
    Create_id = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    role = db.Column(db.String(45), nullable=False)

    def __repr__(self):
        return f'<User {self.Username}>'
