from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, redirect, url_for, render_template, session, request
from flask_sqlalchemy import SQLAlchemy
from Db import db
from Db.models import users, cinema_sessions, seats
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
import psycopg2
from datetime import datetime

app = Flask(__name__)
# прописываем секретный ключ
# он обеспечит безопасность генерируемого JWT-токена
app.secret_key = "123"

user_db = "son_cinema_orm"
host_ip = "127.0.0.1"
host_port = "5432"
database_name = "cinema_son_orm"
password="123"

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{user_db}:{password}@{host_ip}:{host_port}/{database_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# подключаем Flask-Login
login_manager = LoginManager()

# куда редиректить, если пользователь не авторизован,
# а он пытается попасть на защищенную страницу
login_manager.login_view = "login"
login_manager.init_app(app)

# показываем Flask-Login как и где найти нужного пользователя
@login_manager.user_loader
def load_users(user_id):
    # Метод get вернет объект users с нужным id 
    # со всеми атрибутами и методами класса
    return users.query.get(int(user_id))


@app.route("/")
@app.route("/index")
def start():
    return redirect("/cinema", code=302)


@app.route("/cinema/logout")
def logout():
    logout_user()
    return redirect('/cinema')

@app.route("/cinema/delete")
def delete():
    # Получить пользователя
    user = users.query.get(current_user.id)
    # Удалить все места, забронированные пользователем
    seats_to_delete = seats.query.filter_by(reserved_by=current_user.id).all()
    for seat in seats_to_delete:
        db.session.delete(seat)

    # Удалить пользователя из базы данных
    db.session.delete(user)
    db.session.commit()
    # Вернуть пользователя на главную страницу
    return redirect('/cinema')

@app.route("/cinema")
def main():
    if current_user is not None and current_user.is_authenticated:
        visibleUser = current_user.name
    else:
        visibleUser = 'Anon'
    result = users.query.all()
    return render_template("cinema.html", name = visibleUser, result=result)

@app.route("/cinema/addSessions", methods=['GET', 'POST'])
@login_required
def addSessions():
    errors = []
    if current_user.username == "admin":
        if request.method == "POST":
            title_movie = request.form["title_movie"]
            room_num = request.form["room_num"]
            start_time = request.form["start_time"]
            if not title_movie or not room_num or not start_time:
                errors.append("Пожалуйста заполните все поля")
                return render_template("addSessions.html", errors = errors)
            else:
                # Получить максимальный session_id
                session_id = cinema_sessions.query.order_by(cinema_sessions.session_id.desc()).first().session_id
                session_id += 1
                # Добавить сеанс в базу данных
                cin=cinema_sessions(session_id=session_id, movie=title_movie, room_number=room_num, start_time=start_time)
                db.session.add(cin)
                db.session.commit()
                # Добавить номера мест от 1 до 30
                for seat_number in range(1, 31):
                    seat_id = seats.query.order_by(seats.id.desc()).first().id
                    seat_id += 1
                    new_seat = seats(seat_number=seat_number, id=seat_id, session_id=session_id)
                    db.session.add(new_seat)
                db.session.commit()
                return redirect('/cinema')
        return render_template("addSessions.html")
    else:
        return redirect('/cinema')



@app.route('/cinema/register', methods=['GET', 'POST'])
def register():
    errors = []

    if request.method=='GET':
        return render_template('register.html')
    
    name_form=request.form.get('name')
    username_form=request.form.get('username')
    password_form=request.form.get('password')

    isUserExists=users.query.filter_by(username=username_form).first()

    if isUserExists is not None:
        errors.append("Пользователь с данным username уже существует")
        return render_template('register.html', errors=errors)
    elif not (username_form or password_form or name_form):
        errors.append("Пожалуйста заполните все поля")
        return render_template("register.html", errors=errors)
    elif len(password_form) < 5:
        errors.append("Пароль должен содержать не менее 5 символов")
        return render_template("register.html", errors=errors)
    
    # хэшируем пароль
    hashedPswd=generate_password_hash(password_form, method='pbkdf2')
    # создаем объект users с нужными полями
    newUser=users(name=name_form, username=username_form, password=hashedPswd)

    # это INSERT
    db.session.add(newUser)
    # Тоже самое, что и conn.commit()
    db.session.commit()

    return redirect('/cinema/login')



@app.route("/cinema/login", methods=["GET", "POST"])
def login():
    errors = []

    if request.method == "GET":
        return render_template("login.html")
    
    name_form = request.form.get("name")
    username_form = request.form.get("username")
    password_form = request.form.get("password")

    my_user = users.query.filter_by(username = username_form).first()

    if my_user is not None:
        if check_password_hash(my_user.password, password_form):
            # сохраняем JWT токен
            login_user(my_user, remember=False)
            return redirect("/cinema")

    if not (username_form or password_form or name_form):
        errors.append("Пожалуйста заполните все поля")
        return render_template("login.html", errors = errors)
    elif my_user is None:
        errors.append("Такого пользователя не существует")
        return render_template("login.html", errors = errors)
    elif my_user is not check_password_hash(my_user.password, password_form):
        errors.append("Введите правильный пароль")
        return render_template("login.html", errors = errors)

    return render_template("login.html")



@app.route("/cinema/all_sessions", methods=["GET", "POST"])
@login_required
def allFilms():
    movie_sessions = cinema_sessions.query.with_entities(cinema_sessions.movie).distinct().all()
    return render_template("allFilms.html", movie_sessions=movie_sessions)


@app.route("/cinema/movieSessions/<movie>")
@login_required
def movie_sessions(movie):
    # все сеансы для конкретного фильма из базы данных
    sessions = cinema_sessions.query.filter_by(movie = movie).all()
    return render_template("movieSessions.html", movie=movie, sessions=sessions)


@app.route('/cinema/movieSessions/<movie>/deleteSessions', methods=['POST'])
@login_required
def deleteSessions(movie):
    session_id = request.form.get('session_delete')
    seats_to_delete = seats.query.filter_by(session_id=session_id).all()
    for seat in seats_to_delete:
        db.session.delete(seat)
    session = cinema_sessions.query.get(session_id)
    if session:
        db.session.delete(session)
    db.session.commit()
    
    return redirect(f'/cinema/movieSessions/{movie}')



@app.route('/cinema/sessions/<int:session_id>', methods=["GET", "POST"])
@login_required
def session_details(session_id):
    session_data = cinema_sessions.query.filter_by(session_id=session_id).first()
    all_seats = seats.query.filter_by(session_id=session_id).order_by(seats.seat_number.asc()).all()
    all_users = users.query.all()

    # Check if the session start time is in the past
    current_time = datetime.now()
    is_past_session = session_data.start_time < current_time

    return render_template('sessionDetails.html', session_data=session_data, seatss=all_seats,
                           session_id=session_data.session_id, users=all_users, is_past_session=is_past_session)


@app.route('/cinema/sessions/<int:session_id>/booking', methods=['POST'])
@login_required
def booking(session_id):
    seat_id = request.form.get('seat_id')
    seat = seats.query.filter_by(id=seat_id).first()
    if seat.reserved_by is not None:
        return redirect(f'/cinema/sessions/{session_id}')
    seat.reserved_by = current_user.id  
    db.session.commit()
    return redirect(f'/cinema/sessions/{session_id}')


@app.route('/cinema/sessions/<int:session_id>/unbooking', methods=['POST'])
@login_required
def unbooking(session_id):
    seat_id = request.form.get('seat_id')
    seat = seats.query.filter_by(id=seat_id, reserved_by=current_user.id).first()
    admin_seat = seats.query.filter_by(id=seat_id).first()
    if current_user.username == "admin":
        if admin_seat:
            admin_seat.reserved_by = None
            db.session.commit()
    else:
        if seat:
            seat.reserved_by = None
            db.session.commit()
    return redirect(f'/cinema/sessions/{session_id}')
