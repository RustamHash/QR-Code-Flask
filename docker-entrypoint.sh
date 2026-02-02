#!/bin/bash
set -e

echo "=== Инициализация приложения ==="

# Создаем необходимые директории
echo "Создание директорий..."
mkdir -p /app/instance
mkdir -p /app/uploads
mkdir -p /app/static/media

# Устанавливаем права доступа
chmod -R 755 /app/instance /app/uploads 2>/dev/null || true

# Проверяем, что можем писать в директорию instance
echo "Проверка возможности записи в /app/instance..."
touch /app/instance/.test_write 2>/dev/null && rm /app/instance/.test_write && echo "✓ Запись работает" || echo "✗ Проблемы с записью"

# Инициализируем базу данных
echo "Инициализация базы данных..."
python /app/init_db.py 2>&1 || {
    echo "Ошибка при инициализации БД через init_db.py, пробуем создать вручную..."
    python -c "
import os
import sys
from app import app, db
from models import User, UserSettings

try:
    with app.app_context():
        print('Создание таблиц...')
        db.create_all()
        print('✓ Таблицы созданы')
        
        # Создаем пользователя по умолчанию
        default_username = os.environ.get('DEFAULT_USERNAME', 'admin')
        default_password = os.environ.get('DEFAULT_PASSWORD', 'admin123')
        
        existing_user = User.query.filter_by(username=default_username).first()
        if not existing_user:
            user = User(username=default_username, is_admin=1)
            user.set_password(default_password)
            db.session.add(user)
            db.session.commit()
            print(f'✓ Пользователь {default_username} создан')
        else:
            print(f'✓ Пользователь {default_username} уже существует')
except Exception as e:
    print(f'✗ Ошибка: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" || echo "Не удалось создать БД вручную"
}

# Проверяем права на файл БД
if [ -f "/app/instance/database.db" ]; then
    echo "База данных найдена, проверка прав..."
    ls -la /app/instance/database.db
    chmod 664 /app/instance/database.db || true
    chmod 755 /app/instance || true
fi

echo "=== Запуск приложения ==="
exec "$@"
