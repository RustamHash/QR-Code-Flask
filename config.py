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
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///database.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки PDF по умолчанию
    DEFAULT_WIDTH = float(os.environ.get("DEFAULT_WIDTH", "75.0"))
    DEFAULT_HEIGHT = float(os.environ.get("DEFAULT_HEIGHT", "120.0"))
    DEFAULT_ROWS_PER_PAGE = int(os.environ.get("DEFAULT_ROWS_PER_PAGE", "5"))
    DEFAULT_COLUMNS_PER_PAGE = int(os.environ.get("DEFAULT_COLUMNS_PER_PAGE", "1"))
    
    # Настройки файлов
    UPLOAD_FOLDER = "uploads"
    ALLOWED_EXTENSIONS = {"xlsx", "xls", "png", "jpg", "jpeg", "gif", "bmp"}
    
    # Максимальная длина текста
    MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", "10000"))
    
    @staticmethod
    def get_max_file_size_bytes() -> int:
        """Возвращает максимальный размер файла в байтах."""
        return Config.MAX_CONTENT_LENGTH

