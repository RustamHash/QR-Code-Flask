"""
Скрипт инициализации базы данных.
"""
import os
from app import app, db
from models import User, UserSettings

with app.app_context():
    db.create_all()
    
    # Создаем пользователя по умолчанию, если его нет
    default_username = os.environ.get("DEFAULT_USERNAME", "admin")
    default_password = os.environ.get("DEFAULT_PASSWORD", "2103")
    
    existing_user = User.query.filter_by(username=default_username).first()
    if not existing_user:
        # Создаем пользователя напрямую (без вложенного контекста)
        user = User(username=default_username, is_admin=1)
        user.set_password(default_password)
        db.session.add(user)
        db.session.commit()
        print(f"Пользователь '{default_username}' успешно создан!")
        print(f"  - Администратор: Да")
        print(f"  - Пароль: {default_password}")
    else:
        print(f"Пользователь '{default_username}' уже существует!")
    
    print("База данных инициализирована!")