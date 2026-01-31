"""
Скрипт инициализации базы данных.
"""
from app import app, db
from models import User, UserSettings

with app.app_context():
    db.create_all()
    print("База данных инициализирована!")

