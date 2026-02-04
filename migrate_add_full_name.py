"""
Скрипт миграции: добавление поля full_name в таблицу users.
"""
import sqlite3
import os
from app import app, db
from models import User

def migrate_add_full_name():
    """Добавляет колонку full_name в таблицу users, если её нет."""
    with app.app_context():
        # Получаем путь к базе данных
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        if not os.path.exists(db_path):
            print(f"База данных {db_path} не найдена. Создаю новую...")
            db.create_all()
            print("База данных создана!")
            return
        
        # Подключаемся к SQLite напрямую для проверки и добавления колонки
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Проверяем, существует ли колонка full_name
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'full_name' in columns:
                print("Колонка 'full_name' уже существует в таблице users.")
            else:
                print("Добавляю колонку 'full_name' в таблицу users...")
                cursor.execute("ALTER TABLE users ADD COLUMN full_name VARCHAR(200)")
                conn.commit()
                print("Колонка 'full_name' успешно добавлена!")
            
        except Exception as e:
            print(f"Ошибка при миграции: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

if __name__ == "__main__":
    migrate_add_full_name()
    print("Миграция завершена!")
