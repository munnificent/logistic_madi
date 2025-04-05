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

from config import Config

# Создаём базовый класс для наших моделей
Base = declarative_base()

# Создаём engine на основе настроек из config
# Для простоты берем Config.DB_PATH (SQLAlchemy для SQLite: sqlite:///<путь>)
engine = create_engine(f"sqlite:///{Config.DB_PATH}", echo=False)

# Создаём фабрику сессий
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
    name = Column(String, nullable=False)                # Название/номер поезда
    departure_station = Column(String, nullable=True)    # Начальная станция
    arrival_station = Column(String, nullable=True)      # Конечная станция
    departure_time = Column(String, nullable=True)       # Время отправления (в реале может быть DateTime)
    arrival_time = Column(String, nullable=True)         # Время прибытия
    last_operation_station = Column(String, nullable=True)  
    last_operation_time = Column(String, nullable=True)  
    distance_to_arrival = Column(Integer, nullable=True) 
    operation_desc = Column(String, nullable=True)       # Описание операции (Прибытие, Отправление и т.д.)

    # Связь «один-ко-многим» (Train -> Cargo). 
    # Если хотим, чтобы Cargo знал о Train, то в Cargo указываем ForeignKey
    cargos = relationship("Cargo", back_populates="train")

    def __repr__(self):
        return f"<Train(id={self.train_id}, name={self.name})>"

class Cargo(Base):
    """
    Модель "Груз".
    """
    __tablename__ = "cargos"

    cargo_id = Column(Integer, primary_key=True, autoincrement=True)
    cargo_type = Column(String, nullable=True)
    train_id = Column(Integer, ForeignKey("trains.train_id"), nullable=True)
    current_station = Column(String, nullable=True)
    status = Column(String, nullable=True)
    last_stop_time = Column(String, nullable=True)
    next_station = Column(String, nullable=True)
    distance_to_arrival = Column(Integer, nullable=True)
    last_operation = Column(String, nullable=True)

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
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # Для безопасности - хранить хеш
    role = Column(String, nullable=False, default="user")

    def __repr__(self):
        return f"<User(id={self.user_id}, username={self.username})>"

class Contact(Base):
    """
    Модель "Контактное сообщение" (форма обратной связи).
    """
    __tablename__ = "contacts"

    contact_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Contact(id={self.contact_id}, email={self.email})>"

# ------------------------------------
# ФУНКЦИИ ДЛЯ ЗАПОЛНЕНИЯ БАЗОВЫМИ ДАННЫМИ
# ------------------------------------

def create_default_data(session):
    """
    Создаёт тестовые/базовые записи в таблицах (если нужно).
    Можно расширить или убрать в продакшене.
    """
    # Проверим, есть ли уже данные
    has_trains = session.query(Train).first()
    if not has_trains:
        # Создаём пример поезда
        train1 = Train(
            name="KZ-001",
            departure_station="Алматы",
            arrival_station="Астана (Нур-Султан)",
            departure_time="2025-04-10 08:00",
            arrival_time="2025-04-11 20:00",
            last_operation_station="Кокшетау",
            last_operation_time="2025-04-10 15:00",
            distance_to_arrival=350,
            operation_desc="Отправление"
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
            last_operation="Погрузка"
        )
        session.add(cargo1)

    # Создадим пользователя-админа, если его нет
    has_admin = session.query(User).filter_by(username="admin").first()
    if not has_admin:
        admin = User(username="admin", password="123", role="admin")
        session.add(admin)

    # Пример контактного сообщения
    # (В реальном проекте это пользователь пишет через форму)
    # has_contacts = session.query(Contact).first()
    # if not has_contacts:
    #    contact = Contact(name="Тест", email="test@mail.com", message="Hello world")
    #    session.add(contact)

    print("[models] Добавлены дефолтные (тестовые) данные, если их не было.")
