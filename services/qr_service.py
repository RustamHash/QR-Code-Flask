"""
Сервис для генерации QR-кодов.
"""

import io
from typing import List
import qrcode
from qrcode.image.pil import PilImage
import logging

from .exceptions import QRCodeGenerationError

logger = logging.getLogger(__name__)


def generate_qr_code(
    data: str, error_correction: int = qrcode.constants.ERROR_CORRECT_M
) -> PilImage:
    """
    Генерирует QR-код из данных.

    Args:
        data: Данные для кодирования в QR-код
        error_correction: Уровень коррекции ошибок

    Returns:
        PilImage: Изображение QR-кода

    Raises:
        QRCodeGenerationError: если не удалось сгенерировать QR-код
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        logger.debug(f"QR-код сгенерирован для данных длиной {len(data)} символов")
        return img
    except Exception as e:
        logger.error(f"Ошибка при генерации QR-кода: {e}", exc_info=True)
        raise QRCodeGenerationError(f"Не удалось сгенерировать QR-код: {e}") from e


def generate_qr_codes(data_list: List[str]) -> List[PilImage]:
    """
    Генерирует список QR-кодов из списка данных.

    Args:
        data_list: Список данных для кодирования

    Returns:
        List[PilImage]: Список изображений QR-кодов

    Raises:
        QRCodeGenerationError: если не удалось сгенерировать QR-коды
    """
    try:
        qr_images = []
        for i, data in enumerate(data_list, 1):
            img = generate_qr_code(data)
            qr_images.append(img)
            logger.debug(f"Сгенерирован QR-код {i}/{len(data_list)}")

        logger.info(f"Успешно сгенерировано {len(qr_images)} QR-кодов")
        return qr_images
    except QRCodeGenerationError:
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации QR-кодов: {e}", exc_info=True)
        raise QRCodeGenerationError(f"Не удалось сгенерировать QR-коды: {e}") from e


def qr_image_to_bytes(img: PilImage, format: str = "PNG") -> bytes:
    """
    Конвертирует изображение QR-кода в байты.

    Args:
        img: Изображение QR-кода
        format: Формат изображения (PNG, JPEG и т.д.)

    Returns:
        bytes: Изображение в виде байтов
    """
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    return buffer.getvalue()

