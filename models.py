from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(13), unique=True, nullable=False)
    status = db.Column(db.String(20), default='available')
    genero = db.Column(db.String(50), nullable=False, default='Não especificado')  # Nova inclusão, para um futuro sistema de pesquisa.
    rentals = db.relationship('Rental', backref='book', lazy=True)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    rentals = db.relationship('Rental', backref='member', lazy=True, cascade="all, delete-orphan")

class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    rent_date = db.Column(db.DateTime, default=datetime.now)
    return_date = db.Column(db.DateTime)
    actual_return_date = db.Column(db.DateTime)
    fine_amount = db.Column(db.Float, default=0.00)

    def calculate_fine(self):
        if self.actual_return_date > self.return_date:
            days_late = (self.actual_return_date - self.return_date).days
            return days_late * 1.00
        else: 
            return 0.00