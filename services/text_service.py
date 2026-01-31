"""
Сервис для обработки текстовых сообщений.
"""

from typing import List, Tuple
import logging

from .exceptions import TextProcessingError
from config import Config

logger = logging.getLogger(__name__)


def process_text_message(text: str) -> Tuple[List[str], bool]:
    """
    Обрабатывает текстовое сообщение и определяет формат.

    Args:
        text: Текст сообщения

    Returns:
        Tuple[List[str], bool]: (список строк для QR-кодов, является ли одной строкой)

    Raises:
        TextProcessingError: если текст невалиден
    """
    try:
        # Проверяем длину текста
        if len(text) > Config.MAX_TEXT_LENGTH:
            raise TextProcessingError(
                f"Длина текста ({len(text)} символов) превышает максимальный лимит ({Config.MAX_TEXT_LENGTH} символов)"
            )

        # Разбиваем на строки
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if not lines:
            raise TextProcessingError("Текст не содержит данных для обработки")

        if len(lines) > 1000:
            raise TextProcessingError(
                f"Количество строк ({len(lines)}) превышает максимальный лимит (1000 строк)"
            )

        # Определяем формат: одна строка или несколько
        is_single_line = len(lines) == 1

        logger.info(
            f"Текст обработан: {len(lines)} строк, "
            f"формат: {'одна строка' if is_single_line else 'несколько строк'}"
        )

        return lines, is_single_line

    except TextProcessingError:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке текста: {e}", exc_info=True)
        raise TextProcessingError(f"Не удалось обработать текст: {e}") from e

