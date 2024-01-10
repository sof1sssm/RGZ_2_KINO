# импортируем переменную db из файла __init__.py
from . import db
from flask_login import UserMixin


class users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)

    # repr - от слова represent
    # мы подсказываем ORM как отображать эти данные в строковом виде
    def __repr__(self):
        return f'id: {self.id}, name: {self.name}'

class cinema_sessions(db.Model):
    session_id = db.Column(db.Integer, primary_key=True)
    movie = db.Column(db.String(255), nullable=False)
    room_number = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)


class seats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('cinema_sessions.session_id'), nullable=False)
    seat_number = db.Column(db.Integer, nullable=False)
    reserved_by = db.Column(db.Integer, db.ForeignKey('users.id'))

