"""
Сервис для создания PDF файлов с QR-кодами.
"""

import io
from typing import List, Optional, Tuple
from fpdf import FPDF
import logging

from .exceptions import PDFGenerationError
from .qr_service import generate_qr_codes, qr_image_to_bytes

logger = logging.getLogger(__name__)


def create_qr_pdf(
    data_items: List[str],
    width: float = 75.0,
    height: float = 120.0,
    rows_per_page: int = 5,
    columns_per_page: int = 1,
    output_file: Optional[io.BytesIO] = None,
) -> io.BytesIO:
    """
    Создает PDF файл с QR-кодами в виде сетки.

    Args:
        data_items: Список данных для QR-кодов
        width: Ширина страницы в мм
        height: Высота страницы в мм
        rows_per_page: Количество строк на странице
        columns_per_page: Количество колонок на странице
        output_file: BytesIO объект для вывода (если None, создается новый)

    Returns:
        io.BytesIO: BytesIO объект с PDF

    Raises:
        PDFGenerationError: если не удалось создать PDF
    """
    try:
        if not data_items:
            raise PDFGenerationError("Список данных пуст")

        logger.info(f"Генерация {len(data_items)} QR-кодов...")
        qr_images = generate_qr_codes(data_items)

        pdf = FPDF(orientation="P", unit="mm", format=(width, height))

        margin_x = 5
        top_margin = 10
        bottom_margin = 5

        available_width = width - (2 * margin_x)
        available_height = height - top_margin - bottom_margin

        qr_size_by_width = (
            available_width / columns_per_page if columns_per_page > 0 else available_width
        )
        qr_size_by_height = (
            available_height / rows_per_page if rows_per_page > 0 else available_height
        )
        qr_size = min(qr_size_by_width, qr_size_by_height)

        if rows_per_page > 1:
            total_rows_height = qr_size * rows_per_page
            total_spacing_height = available_height - total_rows_height
            vertical_spacing = (
                total_spacing_height / (rows_per_page - 1) if rows_per_page > 1 else 0
            )
        else:
            vertical_spacing = 0

        column_positions = []
        if columns_per_page == 1:
            column_positions = [margin_x + (available_width - qr_size) / 2]
        elif columns_per_page == 2:
            column_positions = [margin_x, width - margin_x - qr_size]
        else:
            total_columns_width = qr_size * columns_per_page
            total_horizontal_spacing = available_width - total_columns_width
            horizontal_spacing = (
                total_horizontal_spacing / (columns_per_page - 1) if columns_per_page > 1 else 0
            )

            column_positions.append(margin_x)

            for col in range(1, columns_per_page - 1):
                x_pos = margin_x + col * (qr_size + horizontal_spacing)
                column_positions.append(x_pos)

            column_positions.append(width - margin_x - qr_size)

        start_y = top_margin
        current_row = 0
        current_col = 0
        page_count = 0

        pdf.add_page()
        page_count = 1
        logger.debug("Создана первая страница")

        for i, qr_image in enumerate(qr_images, 1):
            if current_row >= rows_per_page:
                pdf.add_page()
                current_row = 0
                current_col = 0
                page_count += 1
                logger.debug(f"Создана страница {page_count}")

            x_pos = column_positions[current_col]

            if rows_per_page > 1:
                y_pos = start_y + current_row * (qr_size + vertical_spacing)
            else:
                y_pos = top_margin + (available_height - qr_size) / 2

            img_bytes = qr_image_to_bytes(qr_image)
            temp_file = io.BytesIO(img_bytes)

            pdf.image(temp_file, x=x_pos, y=y_pos, w=qr_size, h=qr_size)

            current_col += 1
            if current_col >= columns_per_page:
                current_col = 0
                current_row += 1

        if output_file is None:
            output_file = io.BytesIO()

        pdf.output(output_file)
        output_file.seek(0)

        total_pages = page_count
        logger.info(
            f"PDF файл создан: {len(data_items)} QR-кодов на {total_pages} страницах (сетка {rows_per_page}x{columns_per_page})"
        )
        return output_file

    except PDFGenerationError:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании PDF: {e}", exc_info=True)
        raise PDFGenerationError(f"Не удалось создать PDF файл: {e}") from e


def create_qr_pdf_from_pairs(
    key_value_pairs: List[Tuple[str, str]],
    width: float = 75.0,
    height: float = 120.0,
    rows_per_page: int = 5,
    output_file: Optional[io.BytesIO] = None,
) -> io.BytesIO:
    """
    Создает PDF файл с QR-кодами из пар значений в двух колонках.

    Колонка A -> QR крайне слева
    Колонка B -> QR крайне справа
    """
    try:
        if not key_value_pairs:
            raise PDFGenerationError("Список пар пуст")

        left_values = [pair[0] for pair in key_value_pairs]
        right_values = [pair[1] for pair in key_value_pairs]

        logger.info(
            f"Генерация {len(left_values)} QR-кодов для левой колонки и {len(right_values)} для правой..."
        )
        left_qr_images = generate_qr_codes(left_values)
        right_qr_images = generate_qr_codes(right_values)

        pdf = FPDF(orientation="P", unit="mm", format=(width, height))

        margin_x = 5
        top_margin = 10
        bottom_margin = 5

        available_width = width - (2 * margin_x)
        available_height = height - top_margin - bottom_margin

        horizontal_spacing = 5
        qr_size_by_width = (available_width - horizontal_spacing) / 2
        qr_size_by_height = (
            available_height / rows_per_page if rows_per_page > 0 else available_height
        )
        qr_size = min(qr_size_by_width, qr_size_by_height)

        if rows_per_page > 1:
            total_rows_height = qr_size * rows_per_page
            total_spacing_height = available_height - total_rows_height
            vertical_spacing = total_spacing_height / (rows_per_page - 1)
        else:
            vertical_spacing = 0

        left_x = margin_x
        right_x = width - margin_x - qr_size

        start_y = top_margin

        pdf.add_page()
        page_count = 1

        for i, (left_img, right_img) in enumerate(zip(left_qr_images, right_qr_images)):
            current_row = i % rows_per_page
            if current_row == 0 and i > 0:
                pdf.add_page()
                page_count += 1

            if rows_per_page > 1:
                y_pos = start_y + current_row * (qr_size + vertical_spacing)
            else:
                y_pos = top_margin + (available_height - qr_size) / 2

            left_bytes = qr_image_to_bytes(left_img)
            right_bytes = qr_image_to_bytes(right_img)

            pdf.image(io.BytesIO(left_bytes), x=left_x, y=y_pos, w=qr_size, h=qr_size)
            pdf.image(io.BytesIO(right_bytes), x=right_x, y=y_pos, w=qr_size, h=qr_size)

        if output_file is None:
            output_file = io.BytesIO()

        pdf.output(output_file)
        output_file.seek(0)

        logger.info(
            f"PDF файл создан: {len(key_value_pairs)} пар на {page_count} страницах (2 колонки)"
        )
        return output_file

    except PDFGenerationError:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании PDF: {e}", exc_info=True)
        raise PDFGenerationError(f"Не удалось создать PDF файл: {e}") from e

