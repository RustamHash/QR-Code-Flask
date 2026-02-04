"""
Flask веб-приложение для генерации QR-кодов.
"""
import os
import logging
import uuid
import mimetypes
from functools import wraps
from io import BytesIO
from datetime import datetime
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from models import db, User, Archive, UserSettings, FileStorage, Message
from services.excel_service import read_data_from_excel, read_key_value_pairs_from_excel
from services.text_service import process_text_message
from services.pdf_service import create_qr_pdf, create_qr_pdf_from_pairs
from services.qr_decode_service import decode_qr_from_image
from services.exceptions import (
    ExcelProcessingError,
    TextProcessingError,
    PDFGenerationError,
    QRCodeDecodeError,
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_proto=1,
    x_host=1,
    x_prefix=1
)
app.config.from_object(Config)

# Инициализация базы данных
db.init_app(app)

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Пожалуйста, войдите в систему для доступа к этой странице."
login_manager.login_message_category = "error"

# Создаем необходимые директории
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["STORAGE_FOLDER"], exist_ok=True)
os.makedirs("instance", exist_ok=True)
os.makedirs("static/media", exist_ok=True)


@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя для Flask-Login."""
    return User.query.get(int(user_id))


def allowed_file(filename):
    """Проверяет, разрешен ли тип файла."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def get_user_settings(user_id):
    """Получает настройки пользователя или создает дефолтные."""
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    if not settings:
        settings = UserSettings(
            user_id=user_id,
            width=Config.DEFAULT_WIDTH,
            height=Config.DEFAULT_HEIGHT,
            rows_per_page=Config.DEFAULT_ROWS_PER_PAGE,
            columns_per_page=Config.DEFAULT_COLUMNS_PER_PAGE,
            excel_mode="one_column"
        )
        db.session.add(settings)
        db.session.commit()
    return {
        "width": settings.width,
        "height": settings.height,
        "rows_per_page": settings.rows_per_page,
        "columns_per_page": settings.columns_per_page,
        "excel_mode": settings.excel_mode
    }


@app.route("/favicon.ico")
def favicon():
    """Обработка запроса favicon.ico."""
    return send_from_directory(os.path.join(app.root_path, 'static', 'media'), 'gerb.png', mimetype='image/png')


@app.route("/login", methods=["GET", "POST"])
def login():
    """Страница входа."""
    all_users = User.query.order_by(User.username).all()
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Введите логин и пароль", "error")
            return render_template("login.html", users=all_users)

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash("Успешный вход в систему", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash("Неверный логин или пароль", "error")

    return render_template("login.html", users=all_users)


@app.route("/logout")
@login_required
def logout():
    """Выход из системы."""
    logout_user()
    flash("Вы вышли из системы", "success")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    """Главная страница."""
    return render_template("index.html")


@app.route("/upload_excel", methods=["GET", "POST"])
@login_required
def upload_excel():
    """Загрузка Excel файла и генерация PDF шаблона."""
    if request.method == "GET":
        pdf_settings = get_user_settings(current_user.id)
        return render_template("upload_excel.html", pdf_settings=pdf_settings)

    if "file" not in request.files:
        flash("Файл не выбран", "error")
        return redirect(url_for("upload_excel"))

    file = request.files["file"]
    if file.filename == "":
        flash("Файл не выбран", "error")
        return redirect(url_for("upload_excel"))

    if not allowed_file(file.filename):
        flash("Недопустимый тип файла. Разрешены: .xlsx, .xls", "error")
        return redirect(url_for("upload_excel"))

    try:
        width = float(request.form.get("width", Config.DEFAULT_WIDTH))
        height = float(request.form.get("height", Config.DEFAULT_HEIGHT))
        rows = int(request.form.get("rows", Config.DEFAULT_ROWS_PER_PAGE))
        columns = int(request.form.get("columns", Config.DEFAULT_COLUMNS_PER_PAGE))
        excel_mode = request.form.get("excel_mode", "one_column")
        
        # Сохраняем настройки
        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if settings:
            settings.excel_mode = excel_mode
        else:
            settings = UserSettings(
                user_id=current_user.id,
                excel_mode=excel_mode,
                width=width,
                height=height,
                rows_per_page=rows,
                columns_per_page=columns
            )
            db.session.add(settings)
        db.session.commit()

        file_bytes = BytesIO(file.read())

        qr_count = 0
        if excel_mode == "two_columns":
            pairs = read_key_value_pairs_from_excel(file_bytes)
            pdf_buffer = create_qr_pdf_from_pairs(
                pairs, width=width, height=height, rows_per_page=rows
            )
            qr_count = len(pairs) * 2
        else:
            data_list = read_data_from_excel(file_bytes)
            pdf_buffer = create_qr_pdf(
                data_list, width=width, height=height, rows_per_page=rows, columns_per_page=columns
            )
            qr_count = len(data_list)

        filename = secure_filename(file.filename)
        pdf_filename = f"{os.path.splitext(filename)[0]}_template.pdf"
        
        pdf_bytes = pdf_buffer.getvalue()
        
        # Сохраняем в архив
        archive = Archive(
            user_id=current_user.id,
            filename=pdf_filename,
            pdf_data=pdf_bytes,
            source_type="excel",
            source_name=filename,
            qr_codes_count=qr_count
        )
        db.session.add(archive)
        db.session.commit()
        
        return send_file(
            BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=False, download_name=pdf_filename
        )

    except ExcelProcessingError as e:
        logger.error(f"Ошибка обработки Excel: {e}")
        flash(f"Ошибка обработки Excel файла: {str(e)}", "error")
        return redirect(url_for("upload_excel"))
    except PDFGenerationError as e:
        logger.error(f"Ошибка генерации PDF: {e}")
        flash(f"Ошибка генерации PDF: {str(e)}", "error")
        return redirect(url_for("upload_excel"))
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        flash(f"Произошла ошибка: {str(e)}", "error")
        return redirect(url_for("upload_excel"))


@app.route("/upload_text", methods=["GET", "POST"])
@login_required
def upload_text():
    """Обработка текста и генерация PDF шаблона."""
    if request.method == "GET":
        pdf_settings = get_user_settings(current_user.id)
        return render_template("upload_text.html", pdf_settings=pdf_settings)

    text = request.form.get("text", "").strip()
    if not text:
        flash("Текст не введен", "error")
        return redirect(url_for("upload_text"))

    try:
        width = float(request.form.get("width", Config.DEFAULT_WIDTH))
        height = float(request.form.get("height", Config.DEFAULT_HEIGHT))
        rows = int(request.form.get("rows", Config.DEFAULT_ROWS_PER_PAGE))
        columns = int(request.form.get("columns", Config.DEFAULT_COLUMNS_PER_PAGE))

        data_list, _ = process_text_message(text)

        pdf_buffer = create_qr_pdf(
            data_list, width=width, height=height, rows_per_page=rows, columns_per_page=columns
        )

        pdf_bytes = pdf_buffer.getvalue()
        
        # Сохраняем в архив
        archive = Archive(
            user_id=current_user.id,
            filename="template_from_text.pdf",
            pdf_data=pdf_bytes,
            source_type="text",
            source_name=f"text ({len(data_list)} строк)",
            qr_codes_count=len(data_list)
        )
        db.session.add(archive)
        db.session.commit()

        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=False,
            download_name="template_from_text.pdf",
        )

    except TextProcessingError as e:
        logger.error(f"Ошибка обработки текста: {e}")
        flash(f"Ошибка обработки текста: {str(e)}", "error")
        return redirect(url_for("upload_text"))
    except PDFGenerationError as e:
        logger.error(f"Ошибка генерации PDF: {e}")
        flash(f"Ошибка генерации PDF: {str(e)}", "error")
        return redirect(url_for("upload_text"))
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        flash(f"Произошла ошибка: {str(e)}", "error")
        return redirect(url_for("upload_text"))


@app.route("/decode_qr", methods=["GET", "POST"])
@login_required
def decode_qr():
    """Обработка изображений для извлечения данных."""
    if request.method == "GET":
        return render_template("decode_qr.html")

    if "file" not in request.files:
        flash("Файл не выбран", "error")
        return redirect(url_for("decode_qr"))

    file = request.files["file"]
    if file.filename == "":
        flash("Файл не выбран", "error")
        return redirect(url_for("decode_qr"))

    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
        flash("Недопустимый тип файла. Разрешены изображения: .png, .jpg, .jpeg, .gif, .bmp", "error")
        return redirect(url_for("decode_qr"))

    try:
        image_bytes = file.read()
        decoded_data = decode_qr_from_image(image_bytes)

        if not decoded_data:
            flash("Данные не найдены на изображении", "error")
            return redirect(url_for("decode_qr"))

        return render_template("decode_result.html", qr_data=decoded_data)

    except QRCodeDecodeError as e:
        logger.error(f"Ошибка декодирования QR: {e}")
        flash(f"Ошибка обработки изображения: {str(e)}", "error")
        return redirect(url_for("decode_qr"))


@app.route("/archive")
@login_required
def archive():
    """Страница архива."""
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    filter_user_id = request.args.get("user_id", type=int)
    date_from_str = request.args.get("date_from", "")
    date_to_str = request.args.get("date_to", "")
    search_query = request.args.get("search", "").strip()

    date_from = None
    date_to = None
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    all_users = []
    if current_user.is_admin == 1:
        all_users = User.query.all()

    if current_user.is_admin == 1:
        filter_user = filter_user_id if filter_user_id else None
    else:
        filter_user = current_user.id

    has_filters = filter_user_id is not None or date_from or date_to or search_query

    query = Archive.query
    if filter_user:
        query = query.filter(Archive.user_id == filter_user)
    if date_from:
        query = query.filter(Archive.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Archive.created_at <= datetime.combine(date_to, datetime.max.time()))
    if search_query:
        query = query.filter(
            Archive.filename.contains(search_query) |
            Archive.source_name.contains(search_query)
        )

    total = query.count()
    archives = query.order_by(Archive.created_at.desc()).limit(per_page).offset(offset).all()
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    filter_params = {
        "user_id": filter_user_id,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "search": search_query,
    }

    return render_template(
        "archive.html",
        archives=archives,
        page=page,
        total_pages=total_pages,
        all_users=all_users,
        filter_params=filter_params,
    )


@app.route("/archive/<int:archive_id>/download")
@login_required
def download_archive(archive_id):
    """Скачивание архива."""
    archive = Archive.query.get_or_404(archive_id)

    if current_user.is_admin != 1 and archive.user_id != current_user.id:
        flash("Нет доступа к этому архиву", "error")
        return redirect(url_for("archive"))

    return send_file(
        BytesIO(archive.pdf_data),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=archive.filename
    )


@app.route("/archive/<int:archive_id>/print")
@login_required
def print_archive(archive_id):
    """Печать архива."""
    archive = Archive.query.get_or_404(archive_id)

    if current_user.is_admin != 1 and archive.user_id != current_user.id:
        flash("Нет доступа к этому архиву", "error")
        return redirect(url_for("archive"))

    return send_file(
        BytesIO(archive.pdf_data),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=archive.filename
    )


@app.route("/archive/<int:archive_id>/comment", methods=["POST"])
@login_required
def update_archive_comment(archive_id):
    """Обновление комментария архива."""
    archive = Archive.query.get_or_404(archive_id)

    if current_user.is_admin != 1 and archive.user_id != current_user.id:
        return jsonify({"success": False, "error": "Нет доступа к этому архиву"}), 403

    data = request.get_json()
    comment = data.get("comment", "").strip() if data else ""
    
    archive.comment = comment if comment else None
    db.session.commit()
    
    return jsonify({"success": True})


@app.route("/storage", methods=["GET"])
@login_required
def storage():
    """Страница хранилища файлов."""
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    filter_user_id = request.args.get("user_id", type=int)
    date_from_str = request.args.get("date_from", "")
    date_to_str = request.args.get("date_to", "")
    search_query = request.args.get("search", "").strip()

    date_from = None
    date_to = None
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    all_users = []
    if current_user.is_admin == 1:
        all_users = User.query.all()

    if current_user.is_admin == 1:
        filter_user = filter_user_id if filter_user_id else None
    else:
        filter_user = current_user.id

    query = FileStorage.query
    if filter_user:
        query = query.filter(FileStorage.user_id == filter_user)
    if date_from:
        query = query.filter(FileStorage.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(FileStorage.created_at <= datetime.combine(date_to, datetime.max.time()))
    if search_query:
        query = query.filter(
            FileStorage.original_filename.contains(search_query) |
            FileStorage.description.contains(search_query)
        )

    total = query.count()
    files = query.order_by(FileStorage.created_at.desc()).limit(per_page).offset(offset).all()
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    filter_params = {
        "user_id": filter_user_id,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "search": search_query,
    }

    return render_template(
        "storage.html",
        files=files,
        page=page,
        total_pages=total_pages,
        all_users=all_users,
        filter_params=filter_params,
    )


@app.route("/storage/upload", methods=["POST"])
@login_required
def storage_upload():
    """Загрузка файла в хранилище."""
    if "file" not in request.files:
        flash("Файл не выбран", "error")
        return redirect(url_for("storage"))

    file = request.files["file"]
    if file.filename == "":
        flash("Файл не выбран", "error")
        return redirect(url_for("storage"))

    try:
        # Читаем файл
        file_bytes = file.read()
        file_size = len(file_bytes)
        
        if file_size == 0:
            flash("Файл пустой", "error")
            return redirect(url_for("storage"))

        # Проверяем размер файла
        if file_size > app.config["MAX_CONTENT_LENGTH"]:
            flash(f"Файл слишком большой. Максимальный размер: {app.config['MAX_CONTENT_LENGTH'] / (1024*1024):.0f} MB", "error")
            return redirect(url_for("storage"))

        # Получаем описание (если есть)
        description = request.form.get("description", "").strip()

        # Генерируем уникальное имя файла
        original_filename = secure_filename(file.filename)
        file_ext = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(app.config["STORAGE_FOLDER"], unique_filename)

        # Определяем MIME тип
        mime_type, _ = mimetypes.guess_type(original_filename)

        # Сохраняем файл на диск
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Сохраняем метаданные в БД
        file_storage = FileStorage(
            user_id=current_user.id,
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            description=description if description else None
        )
        db.session.add(file_storage)
        db.session.commit()

        flash(f"Файл '{original_filename}' успешно загружен", "success")
        return redirect(url_for("storage"))

    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}", exc_info=True)
        flash(f"Ошибка при загрузке файла: {str(e)}", "error")
        return redirect(url_for("storage"))


@app.route("/storage/<int:file_id>/download")
@login_required
def storage_download(file_id):
    """Скачивание файла из хранилища."""
    file_storage = FileStorage.query.get_or_404(file_id)

    # Проверка прав доступа
    if current_user.is_admin != 1 and file_storage.user_id != current_user.id:
        flash("Нет доступа к этому файлу", "error")
        return redirect(url_for("storage"))

    # Проверяем существование файла
    if not os.path.exists(file_storage.file_path):
        flash("Файл не найден на диске", "error")
        return redirect(url_for("storage"))

    return send_file(
        file_storage.file_path,
        mimetype=file_storage.mime_type or "application/octet-stream",
        as_attachment=True,
        download_name=file_storage.original_filename
    )


@app.route("/storage/<int:file_id>/delete", methods=["POST"])
@login_required
def storage_delete(file_id):
    """Удаление файла из хранилища."""
    file_storage = FileStorage.query.get_or_404(file_id)

    # Проверка прав доступа
    if current_user.is_admin != 1 and file_storage.user_id != current_user.id:
        flash("Нет доступа к этому файлу", "error")
        return redirect(url_for("storage"))

    try:
        # Удаляем файл с диска
        if os.path.exists(file_storage.file_path):
            os.remove(file_storage.file_path)

        # Удаляем запись из БД
        original_filename = file_storage.original_filename
        db.session.delete(file_storage)
        db.session.commit()

        flash(f"Файл '{original_filename}' успешно удален", "success")
    except Exception as e:
        logger.error(f"Ошибка удаления файла: {e}", exc_info=True)
        flash(f"Ошибка при удалении файла: {str(e)}", "error")
        db.session.rollback()

    return redirect(url_for("storage"))


@app.route("/save_pdf_settings", methods=["POST"])
@login_required
def save_pdf_settings():
    """Сохранение настроек PDF для текущего пользователя."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Нет данных"}), 400

        width = float(data.get("width", Config.DEFAULT_WIDTH))
        height = float(data.get("height", Config.DEFAULT_HEIGHT))
        rows_per_page = int(data.get("rows_per_page", Config.DEFAULT_ROWS_PER_PAGE))
        columns_per_page = int(data.get("columns_per_page", Config.DEFAULT_COLUMNS_PER_PAGE))

        if width < 10 or width > 1000 or height < 10 or height > 1000:
            return jsonify({"success": False, "error": "Ширина и высота должны быть от 10 до 1000 мм"}), 400
        if rows_per_page < 1 or rows_per_page > 50:
            return jsonify({"success": False, "error": "Количество строк должно быть от 1 до 50"}), 400
        if columns_per_page < 1 or columns_per_page > 10:
            return jsonify({"success": False, "error": "Количество колонок должно быть от 1 до 10"}), 400

        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if settings:
            settings.width = width
            settings.height = height
            settings.rows_per_page = rows_per_page
            settings.columns_per_page = columns_per_page
        else:
            settings = UserSettings(
                user_id=current_user.id,
                width=width,
                height=height,
                rows_per_page=rows_per_page,
                columns_per_page=columns_per_page
            )
            db.session.add(settings)
        db.session.commit()
        
        return jsonify({"success": True})

    except ValueError as e:
        return jsonify({"success": False, "error": f"Некорректные значения: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек PDF: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ошибка при сохранении настроек"}), 500


@app.route("/chat")
@login_required
def chat():
    """Страница группового чата."""
    return render_template("chat.html")


@app.route("/chat/messages", methods=["GET"])
@login_required
def chat_messages():
    """Получить все сообщения (для первоначальной загрузки)."""
    try:
        # Получаем последние 100 сообщений
        messages = Message.query.order_by(Message.created_at.desc()).limit(100).all()
        messages.reverse()  # Переворачиваем для отображения от старых к новым
        
        return jsonify({
            "messages": [msg.to_dict() for msg in messages]
        })
    except Exception as e:
        logger.error(f"Ошибка получения сообщений: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ошибка при получении сообщений"}), 500


@app.route("/chat/latest", methods=["GET"])
@login_required
def chat_latest():
    """Получить новые сообщения после указанного ID (для polling)."""
    try:
        last_id = request.args.get("last_id", type=int, default=0)
        
        # Получаем сообщения после указанного ID
        messages = Message.query.filter(Message.id > last_id).order_by(Message.created_at.asc()).all()
        
        return jsonify({
            "messages": [msg.to_dict() for msg in messages],
            "has_more": False
        })
    except Exception as e:
        logger.error(f"Ошибка получения новых сообщений: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ошибка при получении новых сообщений"}), 500


@app.route("/chat/send", methods=["POST"])
@login_required
def chat_send():
    """Отправить сообщение в чат."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Нет данных"}), 400
        
        content = data.get("content", "").strip()
        
        # Валидация
        if not content:
            return jsonify({"success": False, "error": "Сообщение не может быть пустым"}), 400
        
        if len(content) > 5000:
            return jsonify({"success": False, "error": "Сообщение слишком длинное (максимум 5000 символов)"}), 400
        
        # Создаем сообщение
        message = Message(
            user_id=current_user.id,
            content=content
        )
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": message.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"success": False, "error": "Ошибка при отправке сообщения"}), 500


def admin_required(f):
    """Декоратор для проверки прав администратора."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.is_admin != 1:
            flash("Доступ запрещен. Требуются права администратора.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/users")
@login_required
@admin_required
def users():
    """Страница управления пользователями (только для админов)."""
    all_users = User.query.order_by(User.username).all()
    return render_template("users.html", users=all_users)


@app.route("/users/create", methods=["POST"])
@login_required
@admin_required
def create_user():
    """Создание нового пользователя."""
    try:
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        is_admin = request.form.get("is_admin", "0")
        
        # Валидация
        if not username:
            flash("Имя пользователя не может быть пустым", "error")
            return redirect(url_for("users"))
        
        if len(username) > 80:
            flash("Имя пользователя слишком длинное (максимум 80 символов)", "error")
            return redirect(url_for("users"))
        
        if full_name and len(full_name) > 200:
            flash("Имя слишком длинное (максимум 200 символов)", "error")
            return redirect(url_for("users"))
        
        if not password:
            flash("Пароль не может быть пустым", "error")
            return redirect(url_for("users"))
        
        if len(password) < 3:
            flash("Пароль должен содержать минимум 3 символа", "error")
            return redirect(url_for("users"))
        
        # Проверка на существующего пользователя
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(f"Пользователь '{username}' уже существует", "error")
            return redirect(url_for("users"))
        
        # Создание пользователя
        user = User(
            username=username,
            full_name=full_name if full_name else None,
            is_admin=1 if is_admin == "1" else 0
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash(f"Пользователь '{username}' успешно создан", "success")
        return redirect(url_for("users"))
        
    except Exception as e:
        logger.error(f"Ошибка создания пользователя: {e}", exc_info=True)
        db.session.rollback()
        flash(f"Ошибка при создании пользователя: {str(e)}", "error")
        return redirect(url_for("users"))


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    """Редактирование пользователя."""
    user = User.query.get_or_404(user_id)
    
    # Нельзя редактировать самого себя через этот интерфейс (для безопасности)
    if user.id == current_user.id:
        flash("Вы не можете редактировать свой собственный аккаунт через этот интерфейс", "error")
        return redirect(url_for("users"))
    
    if request.method == "POST":
        try:
            username = request.form.get("username", "").strip()
            full_name = request.form.get("full_name", "").strip()
            password = request.form.get("password", "").strip()
            is_admin = request.form.get("is_admin", "0")
            
            # Валидация
            if not username:
                flash("Имя пользователя не может быть пустым", "error")
                return redirect(url_for("edit_user", user_id=user_id))
            
            if len(username) > 80:
                flash("Имя пользователя слишком длинное (максимум 80 символов)", "error")
                return redirect(url_for("edit_user", user_id=user_id))
            
            if full_name and len(full_name) > 200:
                flash("Имя слишком длинное (максимум 200 символов)", "error")
                return redirect(url_for("edit_user", user_id=user_id))
            
            # Проверка на существующего пользователя (если имя изменилось)
            if username != user.username:
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    flash(f"Пользователь '{username}' уже существует", "error")
                    return redirect(url_for("edit_user", user_id=user_id))
            
            # Обновление данных
            user.username = username
            user.full_name = full_name if full_name else None
            user.is_admin = 1 if is_admin == "1" else 0
            
            # Обновление пароля (если указан)
            if password:
                if len(password) < 3:
                    flash("Пароль должен содержать минимум 3 символа", "error")
                    return redirect(url_for("edit_user", user_id=user_id))
                user.set_password(password)
            
            db.session.commit()
            flash(f"Пользователь '{username}' успешно обновлен", "success")
            return redirect(url_for("users"))
            
        except Exception as e:
            logger.error(f"Ошибка редактирования пользователя: {e}", exc_info=True)
            db.session.rollback()
            flash(f"Ошибка при редактировании пользователя: {str(e)}", "error")
            return redirect(url_for("edit_user", user_id=user_id))
    
    return render_template("edit_user.html", user=user)


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    """Удаление пользователя."""
    user = User.query.get_or_404(user_id)
    
    # Нельзя удалить самого себя
    if user.id == current_user.id:
        flash("Вы не можете удалить свой собственный аккаунт", "error")
        return redirect(url_for("users"))
    
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f"Пользователь '{username}' успешно удален", "success")
    except Exception as e:
        logger.error(f"Ошибка удаления пользователя: {e}", exc_info=True)
        db.session.rollback()
        flash(f"Ошибка при удалении пользователя: {str(e)}", "error")
    
    return redirect(url_for("users"))


@app.errorhandler(413)
def too_large(e):
    """Обработка ошибки слишком большого файла."""
    flash(f"Файл слишком большой. Максимальный размер: 20 MB", "error")
    return redirect(url_for("index")), 413


@app.errorhandler(500)
def internal_error(e):
    """Обработка внутренних ошибок сервера."""
    logger.error(f"Внутренняя ошибка сервера: {e}", exc_info=True)
    return render_template("error.html", error="Внутренняя ошибка сервера"), 500


def migrate_add_full_name():
    """Добавляет колонку full_name в таблицу users, если её нет."""
    import sqlite3
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
            logger.info("Добавляю колонку 'full_name' в таблицу users...")
            cursor.execute("ALTER TABLE users ADD COLUMN full_name VARCHAR(200)")
            conn.commit()
            logger.info("Колонка 'full_name' успешно добавлена!")
    except Exception as e:
        logger.error(f"Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    with app.app_context():
        # Выполняем миграцию перед созданием таблиц
        migrate_add_full_name()
        db.create_all()
    
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    
    logger.info(f"Запуск Flask веб-сервера на {host}:{port} (debug={debug})")
    logger.info(f"Тестовый запуск 4")
    app.run(host=host, port=port, debug=debug)

