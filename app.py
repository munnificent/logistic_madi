"""
app.py

Основной файл приложения Flask.
"""

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from config import DevelopmentConfig  # или ProductionConfig
from forms import LoginForm, TrainForm, CargoForm, ContactForm
from models import SessionLocal, Train, Cargo, User, Contact
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy.orm import joinedload

# Flask и конфигурация
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)  # или ProductionConfig

# Если используем Flask-WTF, нужен SECRET_KEY (берётся из config)
app.config["SECRET_KEY"] = app.config.get("SECRET_KEY", "SOME_FALLBACK_KEY")

# ---------------------------------------
# Вспомогательные функции
# ---------------------------------------
@app.errorhandler(Exception)
def all_exception_handler(e):
    app.logger.error(f"Произошла ошибка: {e}", exc_info=True)
    exc_info=True 
    return "Произошла внутренняя ошибка сервера", 500



# Настройка логгера (можно поместить в отдельную функцию, если хотите)
def configure_logging():
    # Создаём обработчик, который пишет в файл error.log.
    # maxBytes=1_000_000 означает, что файл будет ~1 МБ, после чего создаётся новый,
    # а backupCount=3 — сколько «старых» логов хранить.
    file_handler = RotatingFileHandler("error.log", maxBytes=1_000_000, backupCount=3)
    file_handler.setLevel(logging.WARNING)  # Уровень WARNING и выше (ERROR, CRITICAL)

    # Формат: [Время][Уровень][Модуль]: Сообщение
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] in %(module)s: %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Подключаем обработчик к логгеру приложения Flask
    app.logger.addHandler(file_handler)

    # Устанавливаем общий уровень логирования для Flask
    app.logger.setLevel(logging.INFO)

configure_logging()





def get_current_user():
    """Возвращает объект пользователя, который сейчас залогинен, или None."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    db = SessionLocal()
    user = db.query(User).filter_by(user_id=user_id).first()
    db.close()
    return user

def login_required(role=None):
    """
    Декоратор для роутов, требующих авторизации.
    Если указать role='admin', то требуется роль 'admin'.
    """
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not session.get('user_id'):
                flash("Требуется авторизация", "warning")
                return redirect(url_for('login'))
            if role == 'admin':
                if session.get('role') != 'admin':
                    return "Ошибка: недостаточно прав", 403
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ---------------------------------------
# Маршруты (публичная часть)
# ---------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        # Сохраняем в БД
        db = SessionLocal()
        new_msg = Contact(
            name=form.name.data,
            email=form.email.data,
            message=form.message.data
        )
        db.add(new_msg)
        db.commit()
        db.close()
        flash("Сообщение отправлено! Мы свяжемся с вами в ближайшее время.", "success")
        return render_template('contact_success.html', name=form.name.data)
    return render_template('contact.html', form=form)

@app.route('/track', methods=['GET', 'POST'])
def track():
    if request.method == 'POST':
        identifier = request.form.get('identifier')
        search_type = request.form.get('search_type')  # 'cargo' или 'train'
        db = SessionLocal()

        if search_type == 'cargo':
            result = db.query(Cargo).filter_by(cargo_id=identifier).first()
        else:
            result = db.query(Train).filter_by(train_id=identifier).first()

        db.close()

        if not result:
            return render_template('track_result.html', error=True)

        return render_template('track_result.html', result=result, search_type=search_type)
    else:
        return render_template('track.html')

# ---------------------------------------
# Авторизация
# ---------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    print("== LOGIN FORM SUBMITTED? ==", form.is_submitted())
    print("== FORM ERRORS ==", form.errors)
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        print("== USER TRIES ==", username, password)

        db = SessionLocal()
        user = db.query(User).filter_by(username=username, password=password).first()
        db.close()

        if user:
            print("== FOUND USER ==", user)
            session['user_id'] = user.user_id
            session['username'] = user.username
            session['role'] = user.role
            flash("Успешная авторизация!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            print("== USER NOT FOUND OR WRONG PASSWORD ==")
            flash("Неверный логин или пароль", "danger")
    else:
        if request.method == 'POST':
            print("== VALIDATE FAILED OR ERRORS ==")

    return render_template('login.html', form=form)



@app.route('/logout')
def logout():
    session.clear()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for('index'))

# ---------------------------------------
# Админ-панель
# ---------------------------------------

@app.route('/admin')
@login_required(role='admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

# ------ Управление поездами ------

@app.route('/admin/trains')
@login_required(role='admin')
def train_list():
    db = SessionLocal()
    trains = db.query(Train).all()
    db.close()
    return render_template('train_list.html', trains=trains)

@app.route('/admin/trains/add', methods=['GET', 'POST'])
@login_required(role='admin')
def train_add():
    form = TrainForm()
    if form.validate_on_submit():
        db = SessionLocal()
        new_train = Train(
            name=form.name.data,
            departure_station=form.departure_station.data,
            arrival_station=form.arrival_station.data,
            departure_time=form.departure_time.data,
            arrival_time=form.arrival_time.data,
            last_operation_station=form.last_operation_station.data,
            last_operation_time=form.last_operation_time.data,
            distance_to_arrival=form.distance_to_arrival.data,
            operation_desc=form.operation_desc.data
        )
        db.add(new_train)
        db.commit()
        db.close()
        flash("Новый поезд добавлен", "success")
        return redirect(url_for('train_list'))
    return render_template('train_edit.html', form=form, train=None)

@app.route('/admin/trains/edit/<int:train_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def train_edit(train_id):
    db = SessionLocal()
    train_obj = db.query(Train).filter_by(train_id=train_id).first()
    db.close()
    if not train_obj:
        flash("Поезд не найден.", "danger")
        return redirect(url_for('train_list'))

    form = TrainForm(obj=train_obj)  # заполнит поля формы значениями из объекта

    if form.validate_on_submit():
        db = SessionLocal()
        train_to_update = db.query(Train).filter_by(train_id=train_id).first()
        train_to_update.name = form.name.data
        train_to_update.departure_station = form.departure_station.data
        train_to_update.arrival_station = form.arrival_station.data
        train_to_update.departure_time = form.departure_time.data
        train_to_update.arrival_time = form.arrival_time.data
        train_to_update.last_operation_station = form.last_operation_station.data
        train_to_update.last_operation_time = form.last_operation_time.data
        train_to_update.distance_to_arrival = form.distance_to_arrival.data
        train_to_update.operation_desc = form.operation_desc.data
        db.commit()
        db.close()
        flash("Поезд обновлён.", "success")
        return redirect(url_for('train_list'))

    return render_template('train_edit.html', form=form, train=train_obj)

@app.route('/admin/trains/delete/<int:train_id>', methods=['POST'])
@login_required(role='admin')
def train_delete(train_id):
    db = SessionLocal()
    train_obj = db.query(Train).filter_by(train_id=train_id).first()
    if train_obj:
        db.delete(train_obj)
        db.commit()
        flash("Поезд удалён.", "info")
    else:
        flash("Поезд не найден.", "danger")
    db.close()
    return redirect(url_for('train_list'))

# ------ Управление грузами ------

@app.route('/admin/cargos')
@login_required(role='admin')
def cargo_list():
    db = SessionLocal()
    # Загружаем груз + поезд "жадно", чтобы не пытаться загрузить позже.
    cargos = db.query(Cargo).options(joinedload(Cargo.train)).all()
    db.close()
    return render_template('cargo_list.html', cargos=cargos)


@app.route('/admin/cargos/add', methods=['GET', 'POST'])
@login_required(role='admin')
def cargo_add():
    form = CargoForm()
    if form.validate_on_submit():
        db = SessionLocal()
        new_cargo = Cargo(
            cargo_type=form.cargo_type.data,
            train_id=form.train_id.data,
            current_station=form.current_station.data,
            status=form.status.data,
            last_stop_time=form.last_stop_time.data,
            next_station=form.next_station.data,
            distance_to_arrival=form.distance_to_arrival.data,
            last_operation=form.last_operation.data
        )
        db.add(new_cargo)
        db.commit()
        db.close()
        flash("Новый груз добавлен", "success")
        return redirect(url_for('cargo_list'))
    return render_template('cargo_edit.html', form=form, cargo=None)

@app.route('/admin/cargos/edit/<int:cargo_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def cargo_edit(cargo_id):
    db = SessionLocal()
    cargo_obj = db.query(Cargo).filter_by(cargo_id=cargo_id).first()
    db.close()
    if not cargo_obj:
        flash("Груз не найден.", "danger")
        return redirect(url_for('cargo_list'))

    form = CargoForm(obj=cargo_obj)
    if form.validate_on_submit():
        db = SessionLocal()
        cargo_to_update = db.query(Cargo).filter_by(cargo_id=cargo_id).first()
        cargo_to_update.cargo_type = form.cargo_type.data
        cargo_to_update.train_id = form.train_id.data
        cargo_to_update.current_station = form.current_station.data
        cargo_to_update.status = form.status.data
        cargo_to_update.last_stop_time = form.last_stop_time.data
        cargo_to_update.next_station = form.next_station.data
        cargo_to_update.distance_to_arrival = form.distance_to_arrival.data
        cargo_to_update.last_operation = form.last_operation.data
        db.commit()
        db.close()
        flash("Груз обновлён.", "success")
        return redirect(url_for('cargo_list'))

    return render_template('cargo_edit.html', form=form, cargo=cargo_obj)

@app.route('/admin/cargos/delete/<int:cargo_id>', methods=['POST'])
@login_required(role='admin')
def cargo_delete(cargo_id):
    db = SessionLocal()
    cargo_obj = db.query(Cargo).filter_by(cargo_id=cargo_id).first()
    if cargo_obj:
        db.delete(cargo_obj)
        db.commit()
        flash("Груз удалён.", "info")
    else:
        flash("Груз не найден.", "danger")
    db.close()
    return redirect(url_for('cargo_list'))

# ---------------------------------------
# Запуск приложения
# ---------------------------------------
if __name__ == "__main__":
    # Поднимаем локальный сервер
    app.run(host="0.0.0.0", port=5000, debug=False)
