"""
Скрипт инициализации базы данных.
"""
import os
import sqlite3
from app import app, db
from models import User, UserSettings

def migrate_add_full_name():
    """Добавляет колонку full_name в таблицу users, если её нет."""
    # Получаем путь к базе данных
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if not db_uri.startswith('sqlite:///'):
        return  # Не SQLite, пропускаем
    
    db_path = db_uri.replace('sqlite:///', '')
    
    if not os.path.exists(db_path):
        return  # База данных не существует, будет создана через db.create_all()
    
    # Подключаемся к SQLite напрямую для проверки и добавления колонки
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, существует ли колонка full_name
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'full_name' not in columns:
            print("Добавляю колонку 'full_name' в таблицу users...")
            cursor.execute("ALTER TABLE users ADD COLUMN full_name VARCHAR(200)")
            conn.commit()
            print("Колонка 'full_name' успешно добавлена!")
        else:
            print("Колонка 'full_name' уже существует.")
    except Exception as e:
        print(f"Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

with app.app_context():
    # Выполняем миграцию перед созданием таблиц
    migrate_add_full_name()
    
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