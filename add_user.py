"""
Скрипт для добавления пользователя в базу данных.
"""
import sys
from app import app, db
from models import User

def add_user(username, password, is_admin=False):
    """Добавляет пользователя в базу данных."""
    with app.app_context():
        # Проверяем, существует ли пользователь
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"Пользователь '{username}' уже существует!")
            return False
        
        # Создаем нового пользователя
        user = User(username=username, is_admin=1 if is_admin else 0)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        print(f"Пользователь '{username}' успешно создан!")
        print(f"  - Администратор: {'Да' if is_admin else 'Нет'}")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python add_user.py <username> <password> [is_admin]")
        print("Пример: python add_user.py admin password123 1")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    is_admin = len(sys.argv) > 3 and sys.argv[3] == "1"
    
    add_user(username, password, is_admin)

