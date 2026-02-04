"""
Простая конфигурация приложения.
"""
import os
from typing import Optional


class Config:
    """Настройки приложения."""
    
    # Flask настройки
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB
    
    # База данных
    _db_uri = os.environ.get("DATABASE_URL", "sqlite:///./instance/database.db")
    # Убеждаемся, что директория существует для SQLite и используем абсолютный путь
    if _db_uri.startswith("sqlite:///"):
        db_path = _db_uri.replace("sqlite:///", "")
        # Убираем ./ если есть
        if db_path.startswith("./"):
            db_path = db_path[2:]
        # Преобразуем в абсолютный путь
        if not os.path.isabs(db_path):
            # Получаем базовую директорию приложения
            base_dir = os.path.abspath(os.path.dirname(__file__))
            db_path = os.path.join(base_dir, db_path)
        # Создаем директорию если нужно
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        # Используем абсолютный путь для SQLite
        _db_uri = f"sqlite:///{db_path}"
    
    SQLALCHEMY_DATABASE_URI = _db_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки PDF по умолчанию
    DEFAULT_WIDTH = float(os.environ.get("DEFAULT_WIDTH", "75.0"))
    DEFAULT_HEIGHT = float(os.environ.get("DEFAULT_HEIGHT", "120.0"))
    DEFAULT_ROWS_PER_PAGE = int(os.environ.get("DEFAULT_ROWS_PER_PAGE", "5"))
    DEFAULT_COLUMNS_PER_PAGE = int(os.environ.get("DEFAULT_COLUMNS_PER_PAGE", "1"))
    
    # Настройки файлов
    UPLOAD_FOLDER = "uploads"
    ALLOWED_EXTENSIONS = {"xlsx", "xls", "png", "jpg", "jpeg", "gif", "bmp"}
    
    # Настройки хранилища файлов
    STORAGE_FOLDER = "storage"
    
    # Максимальная длина текста
    MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", "10000"))
    
    @staticmethod
    def get_max_file_size_bytes() -> int:
        """Возвращает максимальный размер файла в байтах."""
        return Config.MAX_CONTENT_LENGTH

