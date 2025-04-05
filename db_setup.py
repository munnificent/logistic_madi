#!/usr/bin/env python
"""
db_setup.py

Скрипт для инициализации (пересоздания) базы данных и заполнения тестовыми данными.
Использует SQLAlchemy и модели из models.py.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from config import Config
from models import Base, create_default_data

def init_db(drop_all: bool = True):
    """
    Инициализирует (и при необходимости пересоздаёт) базу данных.
    :param drop_all: Если True, удаляет все существующие таблицы перед созданием.
    """
    # Формируем путь к базе (SQLite) из config
    db_path = Config.DB_PATH  # или DevelopmentConfig/ProductionConfig
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    if drop_all:
        print("[db_setup] Удаляем все таблицы...")
        Base.metadata.drop_all(bind=engine)

    print("[db_setup] Создаём таблицы...")
    Base.metadata.create_all(bind=engine)

    # При желании добавляем базовые/тестовые данные
    with Session(engine) as session:
        create_default_data(session)
        session.commit()

    print("[db_setup] База данных успешно инициализирована.")

if __name__ == "__main__":
    # Можно указать, хотим ли мы дропнуть все таблицы или нет
    init_db(drop_all=True)
