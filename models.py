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
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Integer, default=0, nullable=False)  # 0 = обычный, 1 = админ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Связи
    archives = db.relationship("Archive", backref="user", lazy=True, cascade="all, delete-orphan")
    settings = db.relationship("UserSettings", backref="user", uselist=False, cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        """Устанавливает пароль пользователя."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Проверяет пароль пользователя."""
        return check_password_hash(self.password_hash, password)
    
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

