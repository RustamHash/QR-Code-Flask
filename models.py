"""
Модели базы данных.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Модель пользователя."""
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(200), nullable=True)  # Полное имя пользователя
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Integer, default=0, nullable=False)  # 0 = обычный, 1 = админ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Связи
    archives = db.relationship("Archive", backref="user", lazy=True, cascade="all, delete-orphan")
    settings = db.relationship("UserSettings", backref="user", uselist=False, cascade="all, delete-orphan")
    file_storage = db.relationship("FileStorage", backref="user", lazy=True, cascade="all, delete-orphan")
    messages = db.relationship("Message", backref="user", lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        """Устанавливает пароль пользователя."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Проверяет пароль пользователя."""
        return check_password_hash(self.password_hash, password)
    
    def get_display_name(self) -> str:
        """Возвращает отображаемое имя (full_name если есть, иначе username)."""
        return self.full_name if self.full_name else self.username
    
    def __repr__(self):
        return f"<User {self.username}>"


class Archive(db.Model):
    """Модель архива PDF файлов."""
    __tablename__ = "archives"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    pdf_data = db.Column(db.LargeBinary, nullable=False)
    source_type = db.Column(db.String(50), nullable=True)  # "excel", "text"
    source_name = db.Column(db.String(255), nullable=True)  # Имя исходного файла или описание
    qr_codes_count = db.Column(db.Integer, default=0, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    @property
    def file_size(self) -> int:
        """Возвращает размер файла в байтах."""
        return len(self.pdf_data) if self.pdf_data else 0
    
    def __repr__(self):
        return f"<Archive {self.filename}>"


class UserSettings(db.Model):
    """Настройки пользователя для PDF."""
    __tablename__ = "user_settings"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    width = db.Column(db.Float, default=75.0, nullable=False)
    height = db.Column(db.Float, default=120.0, nullable=False)
    rows_per_page = db.Column(db.Integer, default=5, nullable=False)
    columns_per_page = db.Column(db.Integer, default=1, nullable=False)
    excel_mode = db.Column(db.String(20), default="one_column", nullable=False)  # "one_column" или "two_columns"
    
    def __repr__(self):
        return f"<UserSettings user_id={self.user_id}>"


class FileStorage(db.Model):
    """Модель хранилища файлов."""
    __tablename__ = "file_storage"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)  # Уникальное имя на диске
    original_filename = db.Column(db.String(255), nullable=False)  # Оригинальное имя
    file_path = db.Column(db.String(500), nullable=False)  # Полный путь
    file_size = db.Column(db.Integer, nullable=False)  # Размер в байтах
    mime_type = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<FileStorage {self.original_filename}>"


class Message(db.Model):
    """Модель сообщений чата."""
    __tablename__ = "messages"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def to_dict(self):
        """Преобразует сообщение в словарь для JSON."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username,
            "full_name": self.user.full_name,
            "display_name": self.user.get_display_name(),
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "is_admin": self.user.is_admin == 1
        }
    
    def __repr__(self):
        return f"<Message {self.id} by {self.user.username}>"

