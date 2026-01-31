"""
Сервис для декодирования QR-кодов из изображений.
"""

import io
from typing import List
from PIL import Image, ImageEnhance, ImageFilter
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol
import logging

from .exceptions import QRCodeDecodeError

logger = logging.getLogger(__name__)


def decode_qr_from_image(image_bytes: bytes) -> List[str]:
    """
    Декодирует QR-коды из изображения.

    Args:
        image_bytes: Изображение в виде байтов

    Returns:
        List[str]: Список данных, извлеченных из QR-кодов

    Raises:
        QRCodeDecodeError: если не удалось декодировать QR-коды
    """
    try:
        # Открываем изображение
        image = Image.open(io.BytesIO(image_bytes))
        logger.info(
            f"Открыто изображение: размер={image.size}, режим={image.mode}, формат={image.format}"
        )

        # Пробуем разные варианты обработки
        decode_attempts = []

        # Конвертируем в grayscale для всех вариантов
        gray_image = image.convert("L")

        # Вариант 1: Простое grayscale
        decode_attempts.append(("grayscale", gray_image))

        # Вариант 2: Увеличенный контраст в grayscale
        enhancer = ImageEnhance.Contrast(gray_image)
        high_contrast = enhancer.enhance(2.0)
        decode_attempts.append(("high_contrast_grayscale", high_contrast))

        # Вариант 3: Максимальный контраст
        max_contrast = enhancer.enhance(3.0)
        decode_attempts.append(("max_contrast_grayscale", max_contrast))

        # Вариант 4: Увеличенная резкость в grayscale
        sharpness_enhancer = ImageEnhance.Sharpness(gray_image)
        sharp_image = sharpness_enhancer.enhance(2.0)
        decode_attempts.append(("sharp_grayscale", sharp_image))

        # Вариант 5: Бинаризация (черно-белое с порогом)
        try:
            for threshold in [128, 100, 150]:
                binary = gray_image.point(lambda x: 255 if x > threshold else 0, mode="1")
                binary_l = binary.convert("L")
                decode_attempts.append((f"binary_threshold_{threshold}", binary_l))
        except Exception as e:
            logger.debug(f"Ошибка при бинаризации: {e}")

        # Вариант 6: Инверсия цветов
        inverted = Image.eval(gray_image, lambda x: 255 - x)
        decode_attempts.append(("inverted_grayscale", inverted))

        # Вариант 7: Инверсия с высоким контрастом
        inverted_contrast = ImageEnhance.Contrast(inverted).enhance(2.0)
        decode_attempts.append(("inverted_high_contrast", inverted_contrast))

        # Вариант 8: RGB
        if image.mode != "RGB":
            rgb_image = image.convert("RGB")
            decode_attempts.append(("RGB", rgb_image))
        else:
            decode_attempts.append(("RGB", image))

        # Вариант 9: Применение фильтра резкости
        sharpened = gray_image.filter(ImageFilter.SHARPEN)
        decode_attempts.append(("sharpened_filter", sharpened))

        # Вариант 10: Увеличенное изображение
        if image.size[0] < 500 or image.size[1] < 500:
            large_gray = gray_image.resize(
                (image.size[0] * 2, image.size[1] * 2), Image.Resampling.LANCZOS
            )
            decode_attempts.append(("resized_2x_grayscale", large_gray))
            large_contrast = ImageEnhance.Contrast(large_gray).enhance(2.0)
            decode_attempts.append(("resized_2x_high_contrast", large_contrast))

        # Пробуем декодировать с каждым вариантом
        decoded_objects = None
        successful_method = None

        for method_name, processed_image in decode_attempts:
            try:
                logger.debug(
                    f"Пробуем метод: {method_name}, размер={processed_image.size}, режим={processed_image.mode}"
                )
                decoded_objects = pyzbar.decode(processed_image, symbols=[ZBarSymbol.QRCODE])
                if decoded_objects:
                    successful_method = method_name
                    logger.info(f"QR-код успешно декодирован методом: {method_name}")
                    break
            except Exception as e:
                logger.debug(f"Метод {method_name} не сработал: {e}")
                continue

        # Если ничего не сработало, пробуем еще более агрессивные методы
        if not decoded_objects:
            logger.debug("Пробуем дополнительные методы обработки")
            if image.size[0] < 500 or image.size[1] < 500:
                for scale in [3, 4, 5]:
                    large_gray = gray_image.resize(
                        (image.size[0] * scale, image.size[1] * scale), Image.Resampling.LANCZOS
                    )
                    for contrast_level in [1.5, 2.0, 3.0]:
                        enhanced = ImageEnhance.Contrast(large_gray).enhance(contrast_level)
                        try:
                            decoded_objects = pyzbar.decode(enhanced, symbols=[ZBarSymbol.QRCODE])
                            if decoded_objects:
                                successful_method = f"resized_{scale}x_contrast_{contrast_level}"
                                logger.info(f"QR-код декодирован методом: {successful_method}")
                                break
                        except:
                            continue
                    if decoded_objects:
                        break

        if not decoded_objects:
            raise QRCodeDecodeError("QR-код не найден на изображении")

        # Извлекаем данные
        data_list = []
        for obj in decoded_objects:
            try:
                data = obj.data.decode("utf-8")
                data_list.append(data)
                logger.debug(f"Декодирован QR-код: {data[:50]}...")
            except UnicodeDecodeError:
                try:
                    data = obj.data.decode("latin-1")
                    data_list.append(data)
                    logger.debug(f"Декодирован QR-код (latin-1): {data[:50]}...")
                except Exception as e:
                    logger.warning(f"Не удалось декодировать данные QR-кода: {e}")
                    continue

        if not data_list:
            raise QRCodeDecodeError("Не удалось извлечь данные из QR-кодов")

        logger.info(
            f"Успешно декодировано {len(data_list)} QR-код(ов) методом: {successful_method}"
        )
        return data_list

    except QRCodeDecodeError:
        raise
    except Exception as e:
        logger.error(f"Ошибка при декодировании QR-кода: {e}", exc_info=True)
        raise QRCodeDecodeError(f"Не удалось декодировать QR-код: {e}") from e

