"""
models.py

Здесь хранятся определения моделей (ORM) и вспомогательная логика
для работы с базой данных при помощи SQLAlchemy.
"""

import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from sqlalchemy import create_engine
from werkzeug.security import generate_password_hash # <-- Добавлен импорт для хеширования

from config import Config

# Создаём базовый класс для наших моделей
Base = declarative_base()

# Создаём engine на основе настроек из config
# Для простоты берем Config.DB_PATH (SQLAlchemy для SQLite: sqlite:///<путь>)
# echo=False - отключает логирование SQL-запросов в консоль (лучше для продакшена)
engine = create_engine(f"sqlite:///{Config.DB_PATH}", echo=False)

# Создаём фабрику сессий
# expire_on_commit=False - позволяет объектам оставаться доступными после коммита сессии
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# ------------------------
# МОДЕЛИ
# ------------------------

class Train(Base):
    """
    Модель "Поезд".
    """
    __tablename__ = "trains"

    train_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)             # Название/номер поезда (добавлена примерная длина)
    departure_station = Column(String(100), nullable=True) # Начальная станция
    arrival_station = Column(String(100), nullable=True)   # Конечная станция
    # TODO: Рассмотреть использование DateTime вместо String для времени
    departure_time = Column(String, nullable=True)         # Время отправления
    arrival_time = Column(String, nullable=True)           # Время прибытия
    last_operation_station = Column(String(100), nullable=True)
    last_operation_time = Column(String, nullable=True)    # TODO: Рассмотреть DateTime
    distance_to_arrival = Column(Integer, nullable=True)
    operation_desc = Column(String(255), nullable=True)    # Описание операции

    # Связь «один-ко-многим» (Train -> Cargo).
    cargos = relationship("Cargo", back_populates="train", cascade="all, delete-orphan")
    # cascade="all, delete-orphan" означает, что при удалении поезда связанные грузы тоже удалятся

    def __repr__(self):
        return f"<Train(id={self.train_id}, name={self.name})>"

class Cargo(Base):
    """
    Модель "Груз".
    """
    __tablename__ = "cargos"

    cargo_id = Column(Integer, primary_key=True, autoincrement=True)
    cargo_type = Column(String(100), nullable=True)
    train_id = Column(Integer, ForeignKey("trains.train_id"), nullable=True) # Внешний ключ к таблице поездов
    current_station = Column(String(100), nullable=True)
    status = Column(String(50), nullable=True)
    # TODO: Рассмотреть использование DateTime вместо String для времени
    last_stop_time = Column(String, nullable=True)
    next_station = Column(String(100), nullable=True)
    distance_to_arrival = Column(Integer, nullable=True)
    last_operation = Column(String(255), nullable=True)

    # Связь обратно к Train
    train = relationship("Train", back_populates="cargos")

    def __repr__(self):
        return f"<Cargo(id={self.cargo_id}, type={self.cargo_type})>"

class User(Base):
    """
    Модель "Пользователь".
    """
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False) # Добавлена длина
    # password = Column(String, nullable=False) # <-- Старое поле пароля УДАЛЕНО
    password_hash = Column(String(255), nullable=False) # <-- НОВОЕ поле для ХЕША пароля
    role = Column(String(20), nullable=False, default="user") # Добавлена длина

    def __repr__(self):
        return f"<User(id={self.user_id}, username={self.username})>"

    # --- Опциональные методы для удобства работы с паролем ---
    # def set_password(self, password):
    #     """Генерирует хеш и сохраняет его."""
    #     self.password_hash = generate_password_hash(password)

    # def check_password(self, password):
    #     """Проверяет предоставленный пароль против сохраненного хеша."""
    #     from werkzeug.security import check_password_hash
    #     return check_password_hash(self.password_hash, password)
    # --- Конец опциональных методов ---


class Contact(Base):
    """
    Модель "Контактное сообщение" (форма обратной связи).
    """
    __tablename__ = "contacts"

    contact_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=True)
    email = Column(String(120), nullable=True) # Увеличена длина для email
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow) # Дата создания по умолчанию

    def __repr__(self):
        return f"<Contact(id={self.contact_id}, email={self.email})>"

# ------------------------------------
# УТИЛИТАРНЫЕ ФУНКЦИИ
# ------------------------------------

def create_all_tables():
    """Создает все таблицы, определенные через Base."""
    print("[models] Попытка создания таблиц...")
    try:
        Base.metadata.create_all(engine)
        print("[models] Таблицы успешно созданы или уже существуют.")
    except Exception as e:
        print(f"[models] Ошибка при создании таблиц: {e}")


def create_default_data(session):
    """
    Создаёт тестовые/базовые записи в таблицах (если они еще не существуют).
    """
    print("[models] Проверка и добавление дефолтных данных...")
    data_added = False # Флаг, что что-то было добавлено

    # Проверим, есть ли уже поезда
    has_trains = session.query(Train).first()
    if not has_trains:
        print("[models] Создание тестового поезда и груза...")
        # Создаём пример поезда
        train1 = Train(
            name="KZ-001",
            departure_station="Алматы",
            arrival_station="Астана", # Убрал скобки, для консистентности
            departure_time="2025-04-10 08:00", # Формат как строка YYYY-MM-DD HH:MM
            arrival_time="2025-04-11 20:00",
            last_operation_station="Кокшетау",
            last_operation_time="2025-04-10 15:00",
            distance_to_arrival=350,
            operation_desc="Отправление из Кокшетау"
        )
        session.add(train1)

        # Пример груза, связанного с поездом
        cargo1 = Cargo(
            cargo_type="Продовольственные товары",
            train=train1,  # связываем через объект train1
            current_station="Кокшетау",
            status="В пути",
            last_stop_time="2025-04-10 14:30",
            next_station="Астана",
            distance_to_arrival=350,
            last_operation="Отправлен со станции Кокшетау"
        )
        session.add(cargo1)
        data_added = True

    # Создадим пользователя-админа, если его нет
    has_admin = session.query(User).filter_by(username="admin").first()
    if not has_admin:
        print("[models] Создание пользователя 'admin'...")
        # ВАЖНО: Задайте здесь НАДЕЖНЫЙ пароль по умолчанию
        default_admin_password = "ChangeMeImmediately123!" # <-- ОБЯЗАТЕЛЬНО СМЕНИТЕ ЭТОТ ПАРОЛЬ СРАЗУ ПОСЛЕ ПЕРВОГО ЗАПУСКА!
        admin_hashed_password = generate_password_hash(default_admin_password)
        admin = User(
            username="admin",
            password_hash=admin_hashed_password, # <-- Используем хеш
            role="admin"
        )
        session.add(admin)
        print(f"\n[models] ВНИМАНИЕ! Создан пользователь 'admin' с паролем по умолчанию: '{default_admin_password}'.")
        print("[models] ОБЯЗАТЕЛЬНО СМЕНИТЕ ЕГО через админ-панель или скрипт!\n")
        data_added = True

    # Если что-то было добавлено, пытаемся сохранить
    if data_added:
        try:
            session.commit()
            print("[models] Дефолтные данные успешно добавлены и сохранены.")
        except Exception as e:
            print(f"[models] Ошибка при сохранении дефолтных данных: {e}")
            session.rollback() # Откатываем изменения в случае ошибки
    else:
        print("[models] Дефолтные данные уже существуют, добавление не требуется.")


# --- Пример запуска создания таблиц и данных ---
# Этот блок можно использовать для инициализации БД из командной строки,
# запустив файл: python models.py
if __name__ == "__main__":
    print("--- Запуск инициализации базы данных ---")
    create_all_tables()
    # Создаем сессию для добавления данных
    session = SessionLocal()
    try:
        create_default_data(session)
    finally:
        session.close() # Гарантированно закрываем сессию
    print("--- Инициализация базы данных завершена ---")