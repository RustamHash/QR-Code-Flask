"""
Сервис для обработки Excel файлов.
"""

import io
from typing import List, Tuple, Union
import pandas as pd
import logging

from .exceptions import ExcelProcessingError

logger = logging.getLogger(__name__)


def read_data_from_excel(excel_file: Union[io.BytesIO, str], column_index: int = 0) -> List[str]:
    """
    Читает данные из Excel файла.

    Args:
        excel_file: Путь к файлу или BytesIO объект
        column_index: Индекс колонки для чтения (по умолчанию 0 - первая колонка)

    Returns:
        List[str]: Список данных из колонки

    Raises:
        ExcelProcessingError: если не удалось прочитать файл
    """
    try:
        df = pd.read_excel(excel_file, sheet_name=0, header=None)

        if df.empty:
            raise ExcelProcessingError("Excel файл пуст")

        if column_index >= len(df.columns):
            raise ExcelProcessingError(
                f"Колонка с индексом {column_index} не существует. "
                f"Доступно колонок: {len(df.columns)}"
            )

        column_data = df.iloc[:, column_index]
        data_list = column_data.dropna().astype(str).tolist()
        data_list = [item.strip() for item in data_list if item.strip()]

        if not data_list:
            raise ExcelProcessingError("Не найдено данных в указанной колонке")

        logger.info(f"Прочитано {len(data_list)} записей из Excel файла")
        return data_list

    except pd.errors.EmptyDataError as e:
        logger.error(f"Excel файл пуст: {e}")
        raise ExcelProcessingError("Excel файл пуст или поврежден") from e
    except Exception as e:
        error_msg = str(e).lower()
        if "excel" in error_msg or "xlsx" in error_msg or "xls" in error_msg:
            logger.error(f"Ошибка при чтении Excel файла: {e}")
            raise ExcelProcessingError(f"Не удалось прочитать Excel файл: {e}") from e
        logger.error(f"Неожиданная ошибка при обработке Excel файла: {e}", exc_info=True)
        raise ExcelProcessingError(f"Ошибка при обработке Excel файла: {e}") from e


def read_key_value_pairs_from_excel(excel_file: Union[io.BytesIO, str]) -> List[Tuple[str, str]]:
    """
    Читает пары (колонка A, колонка B) из Excel файла строго из двух колонок.

    Args:
        excel_file: Путь к файлу или BytesIO объект

    Returns:
        List[Tuple[str, str]]: Список кортежей (значение_из_A, значение_из_B)

    Raises:
        ExcelProcessingError: если не удалось прочитать файл или формат не соответствует
    """
    try:
        df = pd.read_excel(excel_file, sheet_name=0, header=None)

        if df.empty:
            raise ExcelProcessingError("Excel файл пуст")

        df = df.dropna(axis=1, how="all")

        if len(df.columns) != 2:
            raise ExcelProcessingError(
                f"Требуется строго 2 колонки (A и B). Найдено колонок: {len(df.columns)}"
            )

        col_a = df.iloc[:, 0]
        col_b = df.iloc[:, 1]

        pairs: List[Tuple[str, str]] = []
        for idx in range(len(df)):
            a_val = str(col_a.iloc[idx]).strip() if pd.notna(col_a.iloc[idx]) else ""
            b_val = str(col_b.iloc[idx]).strip() if pd.notna(col_b.iloc[idx]) else ""

            if a_val and b_val:
                pairs.append((a_val, b_val))

        if not pairs:
            raise ExcelProcessingError("Не найдено пар значений: заполните обе колонки A и B")

        logger.info(f"Прочитано {len(pairs)} пар значений из Excel файла")
        return pairs

    except pd.errors.EmptyDataError as e:
        logger.error(f"Excel файл пуст: {e}")
        raise ExcelProcessingError("Excel файл пуст или поврежден") from e
    except ExcelProcessingError:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "excel" in error_msg or "xlsx" in error_msg or "xls" in error_msg:
            logger.error(f"Ошибка при чтении Excel файла: {e}")
            raise ExcelProcessingError(f"Не удалось прочитать Excel файл: {e}") from e
        logger.error(f"Неожиданная ошибка при обработке Excel файла: {e}", exc_info=True)
        raise ExcelProcessingError(f"Ошибка при обработке Excel файла: {e}") from e

