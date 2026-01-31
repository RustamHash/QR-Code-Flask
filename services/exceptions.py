"""
Упрощённые исключения для приложения.
"""


class ExcelProcessingError(Exception):
    """Ошибка обработки Excel файла."""
    pass


class TextProcessingError(Exception):
    """Ошибка обработки текста."""
    pass


class QRCodeGenerationError(Exception):
    """Ошибка генерации QR-кода."""
    pass


class QRCodeDecodeError(Exception):
    """Ошибка декодирования QR-кода."""
    pass


class PDFGenerationError(Exception):
    """Ошибка генерации PDF."""
    pass

