import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env (если он есть)
load_dotenv()

class Config:
    """Базовые настройки для всего приложения."""
    SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY") 
    # Если в .env нет SECRET_KEY, подставляется "SUPER_SECRET_KEY"

    # Путь к SQLite-файлу. Можно задать и через .env, например:
    # DB_PATH="sqlite:///C:/myproject/database.db" или относительный.
    DB_PATH = os.getenv("DB_PATH", "database.db")

    # Пример дополнительной настройки
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

class ProductionConfig(Config):
    """Настройки для продакшена."""
    DEBUG = False
    # Можно переопределять или добавлять специальные параметры

class DevelopmentConfig(Config):
    """Настройки для разработки."""
    DEBUG = True
    # Например, включить дебаг-режим, выключить кэш, и т.д.
