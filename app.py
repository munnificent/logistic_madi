"""
app.py

Основной файл приложения Flask.
"""
import os
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, abort
)
from werkzeug.security import generate_password_hash, check_password_hash # <-- Для паролей
from config import DevelopmentConfig # или ProductionConfig
from forms import LoginForm, TrainForm, CargoForm, ContactForm
from models import SessionLocal, Train, Cargo, User, Contact # Убедитесь, что User импортирован
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy.orm import joinedload, Session as SQLAlchemySession # <-- Для type hint
from functools import wraps

# Flask и конфигурация
app = Flask(__name__)
app.config.from_object(DevelopmentConfig) # или ProductionConfig

# Если используем Flask-WTF, нужен SECRET_KEY (берётся из config)
# Убедитесь, что он СЕКРЕТНЫЙ в ProductionConfig и берется из env
app.config["SECRET_KEY"] = app.config.get("SECRET_KEY", "dev-secret-key-replace-in-prod")

# ---------------------------------------
# Настройка логгера
# ---------------------------------------
def configure_logging():
    if not app.debug: # Не настраиваем файловый логгер в debug режиме
        file_handler = RotatingFileHandler(
            "error.log", maxBytes=1_000_000, backupCount=3
        )
        file_handler.setLevel(logging.WARNING)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] in %(module)s: %(message)s"
        )
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)

    # Устанавливаем общий уровень логирования для Flask
    app.logger.setLevel(logging.INFO)
    app.logger.info("Логирование настроено.")

configure_logging()

# ---------------------------------------
# Обработчики ошибок
# ---------------------------------------
@app.errorhandler(Exception)
def all_exception_handler(e):
    # Логируем полную ошибку
    app.logger.error(f"Произошла необработанная ошибка: {e}", exc_info=True)
    # Пользователю показываем общее сообщение
    return render_template("error_500.html"), 500 # Лучше иметь шаблон для ошибок

@app.errorhandler(404)
def page_not_found(e):
    app.logger.warning(f"Запрошен несуществующий URL: {request.url}")
    return render_template("error_404.html"), 404 # И шаблон для 404

@app.errorhandler(403)
def forbidden(e):
    app.logger.warning(f"Доступ запрещен к {request.url} для пользователя {session.get('username')}")
    return render_template("error_403.html"), 403 # И шаблон для 403

# ---------------------------------------
# Вспомогательные функции и декораторы
# ---------------------------------------
def get_db() -> SQLAlchemySession:
    """Фабрика для получения сессии БД."""
    return SessionLocal()

# Контекстный менеджер для сессий (альтернатива постоянному with)
@app.teardown_appcontext
def shutdown_session(exception=None):
    # Этот подход менее явный, чем with, но тоже работает,
    # если не использовать with SessionLocal() as db: везде.
    # Оставим with SessionLocal() as db: для явности.
    pass

def get_current_user():
    """Возвращает объект пользователя из БД, если он залогинен, иначе None."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    try:
        with SessionLocal() as db:
            user = db.query(User).filter_by(user_id=user_id).first()
        return user
    except Exception as e:
        app.logger.error(f"Ошибка при получении пользователя {user_id}: {e}", exc_info=True)
        return None

def login_required(role=None):
    """
    Декоратор для роутов, требующих авторизации.
    Проверяет наличие user_id в сессии и опционально роль.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Для доступа к этой странице требуется авторизация.", "warning")
                return redirect(url_for('login', next=request.url)) # next для редиректа обратно
            if role == 'admin' and session.get('role') != 'admin':
                app.logger.warning(
                    f"Пользователь {session.get('username')} ({session.get('user_id')}) "
                    f"попытался получить доступ к admin-ресурсу {request.url} без прав."
                )
                abort(403) # Вызываем ошибку "Доступ запрещен"
            # Можно добавить вызов get_current_user() и передать его в view, если нужно
            # kwargs['current_user'] = get_current_user()
            return f(*args, **kwargs)
        return decorated_function
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
        try:
            with SessionLocal() as db:
                new_msg = Contact(
                    name=form.name.data,
                    email=form.email.data,
                    message=form.message.data
                )
                db.add(new_msg)
                db.commit()
            flash("Сообщение отправлено! Мы свяжемся с вами.", "success")
            # Можно редиректить, чтобы избежать повторной отправки при обновлении
            return redirect(url_for('contact_success'))
        except Exception as e:
            app.logger.error(f"Ошибка при сохранении сообщения: {e}", exc_info=True)
            flash("Произошла ошибка при отправке сообщения.", "danger")
            # Остаемся на той же странице с формой
            
    return render_template('contact.html', form=form)

@app.route('/contact/success')
def contact_success():
    # Простая страница подтверждения
    return render_template('contact_success.html')


@app.route('/track', methods=['GET', 'POST'])
def track():
    result = None
    search_type = None
    error = False
    identifier_input = None # Сохраним оригинальный ввод пользователя

    if request.method == 'POST':
        identifier_input = request.form.get('identifier', '').strip()
        search_type = request.form.get('search_type') # 'cargo' или 'train'
        app.logger.info(f"Попытка отслеживания: Тип={search_type}, Идентификатор='{identifier_input}'") # Логируем ввод

        if not identifier_input or not search_type:
            flash("Введите идентификатор и выберите тип для поиска.", "warning")
            return render_template('track.html', identifier=identifier_input)

        # --- Начало изменений ---
        try:
            # Пытаемся преобразовать идентификатор в число
            identifier_int = int(identifier_input)
        except ValueError:
            app.logger.warning(f"Не удалось преобразовать идентификатор '{identifier_input}' в число.")
            flash(f"Идентификатор '{identifier_input}' должен быть числом.", "danger")
            error = True
            # Сразу выходим, если ID не числовой
            return render_template('track.html', error=error, identifier=identifier_input, search_type=search_type)
        # --- Конец изменений ---

        # Если преобразование удалось, продолжаем поиск
        try:
            with SessionLocal() as db:
                if search_type == 'cargo':
                    result = db.query(Cargo).options(joinedload(Cargo.train)).filter(Cargo.cargo_id == identifier_int).first() # Используем identifier_int
                elif search_type == 'train':
                    result = db.query(Train).filter(Train.train_id == identifier_int).first() # Используем identifier_int
                else:
                    flash("Неверный тип поиска.", "danger")
                    error = True # Не должно произойти, если форма правильная

            if result:
                 app.logger.info(f"Найден результат для {search_type} ID {identifier_int}")
            elif not error: # Только если не было ошибки типа поиска
                app.logger.warning(f"Объект не найден: Тип={search_type}, ID={identifier_int}")
                flash(f"Объект с идентификатором '{identifier_input}' не найден.", "warning")
                error = True

        except Exception as e:
            app.logger.error(f"Ошибка при поиске {search_type} с ID {identifier_input} (int: {identifier_int}): {e}", exc_info=True)
            flash("Произошла ошибка при поиске.", "danger")
            error = True

        # Отображаем результат (или его отсутствие)
        return render_template('track.html', result=result, search_type=search_type, error=error, identifier=identifier_input)

    # Для GET запроса просто показываем форму
    return render_template('track.html')

# ---------------------------------------
# Авторизация
# ---------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard')) # Уже залогинен

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        app.logger.info(f"Попытка входа пользователя: {username}")

        try:
            with SessionLocal() as db:
                user = db.query(User).filter(User.username == username).first()

            # Проверяем пользователя и хеш пароля
            if user and check_password_hash(user.password_hash, password): # <-- Проверка хеша
                session.clear() # На всякий случай чистим старую сессию
                session['user_id'] = user.user_id
                session['username'] = user.username
                session['role'] = user.role
                app.logger.info(f"Успешный вход пользователя: {username} (ID: {user.user_id})")
                flash("Успешная авторизация!", "success")

                # Редирект на страницу, с которой пришли, или на дашборд
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('admin_dashboard'))
            else:
                app.logger.warning(f"Неудачная попытка входа для пользователя: {username}")
                flash("Неверный логин или пароль.", "danger")

        except Exception as e:
            app.logger.error(f"Ошибка при попытке входа пользователя {username}: {e}", exc_info=True)
            flash("Произошла ошибка сервера при попытке входа.", "danger")

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required() # Простой login_required, чтобы нельзя было выйти не залогинившись
def logout():
    username = session.get('username', 'N/A')
    user_id = session.get('user_id', 'N/A')
    session.clear()
    app.logger.info(f"Пользователь {username} (ID: {user_id}) вышел из системы.")
    flash("Вы успешно вышли из системы.", "info")
    return redirect(url_for('index'))

# --- Команда для создания хеша пароля (запустить в Flask shell или отдельном скрипте) ---
# from werkzeug.security import generate_password_hash
# print(generate_password_hash('ваш_пароль'))
# Полученный хеш нужно сохранить в поле password_hash пользователя в БД
# Убедитесь, что в models.py у User есть поле password_hash (String), а не password.

# ---------------------------------------
# Админ-панель (CRUD операции)
# ---------------------------------------
@app.route('/admin')
@login_required(role='admin')
def admin_dashboard():
    # Можно добавить сюда какую-то статистику или быстрые ссылки
    return render_template('admin_dashboard.html')

# ------ Управление поездами ------
@app.route('/admin/trains')
@login_required(role='admin')
def train_list():
    try:
        with SessionLocal() as db:
            trains = db.query(Train).order_by(Train.train_id).all()
        return render_template('train_list.html', trains=trains)
    except Exception as e:
        app.logger.error(f"Ошибка при загрузке списка поездов: {e}", exc_info=True)
        flash("Не удалось загрузить список поездов.", "danger")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/trains/add', methods=['GET', 'POST'])
@login_required(role='admin')
def train_add():
    form = TrainForm()
    if form.validate_on_submit():
        try:
            with SessionLocal() as db:
                new_train = Train()
                form.populate_obj(new_train) # <-- Удобный способ заполнить объект из формы
                db.add(new_train)
                db.commit()
                flash(f"Поезд '{new_train.name}' успешно добавлен.", "success")
                app.logger.info(f"Пользователь {session['username']} добавил поезд ID {new_train.train_id}")
            return redirect(url_for('train_list'))
        except Exception as e:
            app.logger.error(f"Ошибка при добавлении поезда: {e}", exc_info=True)
            flash("Произошла ошибка при добавлении поезда.", "danger")
            db.rollback() # Откатываем транзакцию в случае ошибки

    return render_template('train_edit.html', form=form, title="Добавить поезд", train=None) # Передаем заголовок

@app.route('/admin/trains/edit/<int:train_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def train_edit(train_id):
    try:
        with SessionLocal() as db:
            # Получаем поезд и сразу используем его в сессии
            train_obj = db.query(Train).filter_by(train_id=train_id).first()
            if not train_obj:
                flash("Поезд не найден.", "danger")
                return redirect(url_for('train_list'))

            # Создаем форму, заполняя её данными из объекта, если GET
            # Если POST и валидация не прошла, WTForms сама подставит введенные данные
            form = TrainForm(obj=train_obj if request.method == 'GET' else None)

            if form.validate_on_submit():
                form.populate_obj(train_obj) # Обновляем объект данными из формы
                db.commit() # Фиксируем изменения
                flash(f"Поезд '{train_obj.name}' успешно обновлен.", "success")
                app.logger.info(f"Пользователь {session['username']} обновил поезд ID {train_id}")
                return redirect(url_for('train_list'))

    except Exception as e:
        app.logger.error(f"Ошибка при редактировании поезда {train_id}: {e}", exc_info=True)
        flash("Произошла ошибка при сохранении изменений.", "danger")
        # Не делаем редирект, чтобы пользователь видел ошибки валидации или сообщение

    # Для GET запроса или если POST не прошел валидацию
    return render_template('train_edit.html', form=form, title=f"Редактировать поезд: {train_obj.name}", train=train_obj)


@app.route('/admin/trains/delete/<int:train_id>', methods=['POST']) # Только POST для удаления
@login_required(role='admin')
def train_delete(train_id):
    try:
        with SessionLocal() as db:
            train_obj = db.query(Train).filter_by(train_id=train_id).first()
            if train_obj:
                train_name = train_obj.name # Сохраним имя для сообщения
                db.delete(train_obj)
                db.commit()
                flash(f"Поезд '{train_name}' удалён.", "info")
                app.logger.info(f"Пользователь {session['username']} удалил поезд ID {train_id}")
            else:
                flash("Поезд не найден.", "danger")
                app.logger.warning(f"Пользователь {session['username']} пытался удалить несуществующий поезд ID {train_id}")
    except Exception as e:
        app.logger.error(f"Ошибка при удалении поезда {train_id}: {e}", exc_info=True)
        flash("Произошла ошибка при удалении поезда.", "danger")
        db.rollback() # Откатываем на всякий случай

    return redirect(url_for('train_list'))


# ------ Управление грузами (аналогично поездам) ------

@app.route('/admin/cargos')
@login_required(role='admin')
def cargo_list():
    try:
        with SessionLocal() as db:
            cargos = db.query(Cargo).options(joinedload(Cargo.train)).order_by(Cargo.cargo_id).all()
        return render_template('cargo_list.html', cargos=cargos)
    except Exception as e:
        app.logger.error(f"Ошибка при загрузке списка грузов: {e}", exc_info=True)
        flash("Не удалось загрузить список грузов.", "danger")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/cargos/add', methods=['GET', 'POST'])
@login_required(role='admin')
def cargo_add():
    form = CargoForm()
    # Динамическое заполнение выбора поезда в форме (если это SelectField)
    try:
        with SessionLocal() as db:
            form.train_id.choices = [(t.train_id, t.name) for t in db.query(Train).order_by(Train.name).all()]
    except Exception as e:
        app.logger.error(f"Ошибка загрузки поездов для формы груза: {e}", exc_info=True)
        flash("Ошибка загрузки списка поездов.", "danger")
        # Можно редирект или просто пустой список в форме

    if form.validate_on_submit():
        try:
            with SessionLocal() as db:
                new_cargo = Cargo()
                form.populate_obj(new_cargo)
                # Убедимся, что train_id из формы существует
                train_exists = db.query(Train).filter_by(train_id=new_cargo.train_id).count() > 0
                if not train_exists:
                    flash(f"Ошибка: Поезд с ID {new_cargo.train_id} не найден.", "danger")
                    # Не добавляем, возвращаем форму с ошибкой
                    return render_template('cargo_edit.html', form=form, title="Добавить груз", cargo=None)
                
                db.add(new_cargo)
                db.commit()
                flash(f"Груз '{new_cargo.cargo_type}' (ID: {new_cargo.cargo_id}) успешно добавлен.", "success")
                app.logger.info(f"Пользователь {session['username']} добавил груз ID {new_cargo.cargo_id}")
            return redirect(url_for('cargo_list'))
        except Exception as e:
            app.logger.error(f"Ошибка при добавлении груза: {e}", exc_info=True)
            flash("Произошла ошибка при добавлении груза.", "danger")
            db.rollback()
            # Может потребоваться снова заполнить choices для поезда перед рендером
            try:
                with SessionLocal() as db_retry:
                    form.train_id.choices = [(t.train_id, t.name) for t in db_retry.query(Train).order_by(Train.name).all()]
            except Exception as e_retry:
                 app.logger.error(f"Повторная ошибка загрузки поездов для формы груза: {e_retry}", exc_info=True)


    # Для GET запроса или если POST не прошел валидацию
    return render_template('cargo_edit.html', form=form, title="Добавить груз", cargo=None)


@app.route('/admin/cargos/edit/<int:cargo_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def cargo_edit(cargo_id):
    try:
        with SessionLocal() as db:
            cargo_obj = db.query(Cargo).filter_by(cargo_id=cargo_id).first()
            if not cargo_obj:
                flash("Груз не найден.", "danger")
                return redirect(url_for('cargo_list'))

            # Заполняем choices для поезда в любом случае (GET или POST с ошибкой)
            train_choices = [(t.train_id, t.name) for t in db.query(Train).order_by(Train.name).all()]
            
            # Создаем форму
            form = CargoForm(obj=cargo_obj if request.method == 'GET' else None)
            form.train_id.choices = train_choices

            if form.validate_on_submit():
                # Проверяем существование выбранного поезда перед сохранением
                selected_train_id = form.train_id.data
                train_exists = db.query(Train).filter_by(train_id=selected_train_id).count() > 0
                if not train_exists:
                     flash(f"Ошибка: Поезд с ID {selected_train_id} не найден.", "danger")
                     # Возвращаем форму с ошибкой
                     return render_template('cargo_edit.html', form=form, title=f"Редактировать груз: {cargo_obj.cargo_type}", cargo=cargo_obj)

                form.populate_obj(cargo_obj)
                db.commit()
                flash(f"Груз '{cargo_obj.cargo_type}' (ID: {cargo_id}) успешно обновлен.", "success")
                app.logger.info(f"Пользователь {session['username']} обновил груз ID {cargo_id}")
                return redirect(url_for('cargo_list'))

    except Exception as e:
        app.logger.error(f"Ошибка при редактировании груза {cargo_id}: {e}", exc_info=True)
        flash("Произошла ошибка при сохранении изменений.", "danger")
        # Может потребоваться снова заполнить choices для поезда перед рендером
        try:
            with SessionLocal() as db_retry:
                form.train_id.choices = [(t.train_id, t.name) for t in db_retry.query(Train).order_by(Train.name).all()]
        except Exception as e_retry:
            app.logger.error(f"Повторная ошибка загрузки поездов для формы груза: {e_retry}", exc_info=True)


    # Для GET или POST с ошибкой
    return render_template('cargo_edit.html', form=form, title=f"Редактировать груз: {cargo_obj.cargo_type}", cargo=cargo_obj)


@app.route('/admin/cargos/delete/<int:cargo_id>', methods=['POST'])
@login_required(role='admin')
def cargo_delete(cargo_id):
    try:
        with SessionLocal() as db:
            cargo_obj = db.query(Cargo).filter_by(cargo_id=cargo_id).first()
            if cargo_obj:
                cargo_type = cargo_obj.cargo_type # Сохраним для сообщения
                db.delete(cargo_obj)
                db.commit()
                flash(f"Груз '{cargo_type}' (ID: {cargo_id}) удалён.", "info")
                app.logger.info(f"Пользователь {session['username']} удалил груз ID {cargo_id}")
            else:
                flash("Груз не найден.", "danger")
                app.logger.warning(f"Пользователь {session['username']} пытался удалить несуществующий груз ID {cargo_id}")
    except Exception as e:
        # Обработка возможных ошибок ForeignKeyConstraint, если груз используется где-то еще
        app.logger.error(f"Ошибка при удалении груза {cargo_id}: {e}", exc_info=True)
        flash("Произошла ошибка при удалении груза. Возможно, он связан с другими записями.", "danger")
        db.rollback()

    return redirect(url_for('cargo_list'))

# ---------------------------------------
# Запуск приложения
# ---------------------------------------
if __name__ == "__main__":
    # debug=True удобно для разработки, но НИКОГДА не используйте в продакшене!
    # host="0.0.0.0" нужен для Docker или доступа извне VM/сети.
    app.run(host="0.0.0.0", port=5000, debug=DevelopmentConfig.DEBUG)