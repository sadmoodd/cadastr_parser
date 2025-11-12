# -*- coding: utf-8 -*-
"""
table_builder.py
----------------
Модуль для создания и управления структурой таблицы Excel.
Преобразует извлеченные данные в строки таблицы.
"""

import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path

from logger_cfg import setup_logger
from settings import EXCEL_COLUMNS

# ════════════════════════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ
# ════════════════════════════════════════════════════════════════════════════

logger = setup_logger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# ОСНОВНЫЕ ФУНКЦИИ
# ════════════════════════════════════════════════════════════════════════════

def create_empty_dataframe() -> pd.DataFrame:
    """
    Создает пустой DataFrame с нужной структурой.
    
    Returns:
        pd.DataFrame: Пустая таблица с нужными колонками
    """
    logger.debug(f"Создание пустого DataFrame с {len(EXCEL_COLUMNS)} колонками")
    return pd.DataFrame(columns=EXCEL_COLUMNS)


def create_row_from_extracted_data(
    data: Dict[str, Optional[str]],
    file_name: str,
    row_number: int = 1
) -> Dict:
    """
    Преобразует извлеченные данные в строку таблицы.
    
    Args:
        data: Словарь с извлеченными данными (от data_extractor)
        file_name: Имя исходного PDF файла
        row_number: Номер строки (для колонки "№ п/п")
        
    Returns:
        Dict: Словарь с данными для строки таблицы
        
    Маппинг данных:
    - cadastral_number → "Кадастр. номер ЗУ"
    - address → "Адрес, комплекс"
    - area → "Площадь (м²)"
    - owner → "Собственник"
    - permitted_use → "Предполагаемое назначение"
    - rental_data → "Обременение (аренда)", "Арендатор"
    - file_name → "PDF-источник"
    """
    
    logger.debug(f"Создание строки #{row_number} для {file_name}")
    
    # Инициализируем строку с пустыми значениями
    row = {col: "" for col in EXCEL_COLUMNS}
    
    # Заполняем известные поля
    row["№ п/п"] = row_number
    row["PDF-источник"] = file_name
    
    # Маппинг основных полей
    if data.get('cadastral_number'):
        row["Кадастр. номер ЗУ"] = data['cadastral_number']
    
    if data.get('address'):
        row["Адрес, комплекс"] = data['address']
    
    if data.get('area'):
        row["Площадь (м²)"] = data['area']
    
    if data.get('owner'):
        row["Собственник"] = data['owner']
    
    if data.get('permitted_use'):
        row["Предполагаемое назначение"] = data['permitted_use']
    
    # Обработка информации об аренде
    if data.get('rental_data'):
        rental = data['rental_data']
        
        # Составляем строку с информацией об аренде
        rental_info_parts = []
        
        if rental.get('rent_type'):
            rental_info_parts.append(f"Тип: {rental['rent_type']}")
        
        if rental.get('period_start') and rental.get('period_end'):
            rental_info_parts.append(f"Период: {rental['period_start']} - {rental['period_end']}")
        
        if rental_info_parts:
            row["Обременение (аренда)"] = "; ".join(rental_info_parts)
        
        # Арендатор (тенант)
        if rental.get('tenant'):
            row["Арендатор"] = rental['tenant']
    
    logger.debug(f"Строка #{row_number} создана успешно")
    
    return row


def create_error_row(file_name: str, error_message: str, row_number: int = 1) -> Dict:
    """
    Создает пустую строку при ошибке парсинга.
    
    Args:
        file_name: Имя исходного PDF файла
        error_message: Сообщение об ошибке
        row_number: Номер строки
        
    Returns:
        Dict: Словарь с данными ошибки
    """
    
    logger.warning(f"Создание строки ошибки для {file_name}: {error_message}")
    
    row = {col: "" for col in EXCEL_COLUMNS}
    row["№ п/п"] = row_number
    row["PDF-источник"] = f"{file_name} [ОШИБКА]"
    row["Примечания и расхождения"] = f"Ошибка парсинга: {error_message}"
    
    return row


def add_row_to_dataframe(
    df: pd.DataFrame,
    row: Dict
) -> pd.DataFrame:
    """
    Добавляет строку в DataFrame.
    
    Args:
        df: Существующий DataFrame
        row: Словарь со строкой для добавления
        
    Returns:
        pd.DataFrame: DataFrame с добавленной строкой
    """
    
    new_row_df = pd.DataFrame([row])
    df = pd.concat([df, new_row_df], ignore_index=True)
    
    logger.debug(f"Строка добавлена. Всего строк: {len(df)}")
    
    return df


def add_rows_batch(
    df: pd.DataFrame,
    rows: List[Dict]
) -> pd.DataFrame:
    """
    Добавляет несколько строк в DataFrame за раз (быстрее).
    
    Args:
        df: Существующий DataFrame
        rows: Список словарей со строками
        
    Returns:
        pd.DataFrame: DataFrame с добавленными строками
    """
    
    if not rows:
        return df
    
    new_rows_df = pd.DataFrame(rows)
    df = pd.concat([df, new_rows_df], ignore_index=True)
    
    logger.debug(f"Добавлено {len(rows)} строк. Всего строк: {len(df)}")
    
    return df


def get_dataframe_info(df: pd.DataFrame) -> Dict:
    """
    Возвращает информацию о DataFrame.
    
    Args:
        df: DataFrame
        
    Returns:
        Dict: Информация о таблице
    """
    
    info = {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'columns': list(df.columns),
        'filled_rows': len(df[df['PDF-источник'].notna()]),
        'error_rows': len(df[df['PDF-источник'].str.contains('ОШИБКА', na=False)]),
    }
    
    logger.info(f"DataFrame info: {info['total_rows']} строк, {info['total_columns']} колонок")
    
    return info


def validate_dataframe(df: pd.DataFrame) -> bool:
    """
    Проверяет корректность DataFrame.
    
    Args:
        df: DataFrame для проверки
        
    Returns:
        bool: True если DataFrame корректен
    """
    
    # Проверка колонок
    if list(df.columns) != EXCEL_COLUMNS:
        logger.error("Колонки DataFrame не совпадают с ожидаемыми")
        return False
    
    # Проверка строк
    if len(df) == 0:
        logger.warning("DataFrame пуст (0 строк)")
        return False
    
    logger.debug(f"DataFrame валиден: {len(df)} строк")
    
    return True


def fill_numbers_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Заполняет колонку "№ п/п" последовательными номерами.
    
    Args:
        df: DataFrame
        
    Returns:
        pd.DataFrame: DataFrame с заполненной колонкой номеров
    """
    
    df['№ п/п'] = range(1, len(df) + 1)
    
    logger.debug(f"Колонка '№ п/п' заполнена числами от 1 до {len(df)}")
    
    return df


def sort_by_column(df: pd.DataFrame, column: str = "Кадастр. номер ЗУ") -> pd.DataFrame:
    """
    Сортирует DataFrame по колонке.
    
    Args:
        df: DataFrame
        column: Название колонки для сортировки
        
    Returns:
        pd.DataFrame: Отсортированный DataFrame
    """
    
    if column not in df.columns:
        logger.warning(f"Колонка '{column}' не найдена")
        return df
    
    df_sorted = df.sort_values(by=column, na_position='last')
    
    logger.debug(f"DataFrame отсортирован по '{column}'")
    
    return df_sorted


# ════════════════════════════════════════════════════════════════════════════
# ТЕСТИРОВАНИЕ
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🧪 Тестирование модуля table_builder.py\n")
    
    # 1. Создать пустую таблицу
    print("1️⃣ Создание пустой таблицы...")
    df = create_empty_dataframe()
    print(f"   ✓ Создана таблица с {len(df.columns)} колонками\n")
    
    # 2. Добавить строку с данными
    print("2️⃣ Добавление строки с данными...")
    test_data = {
        'cadastral_number': '74:36:0303005:454',
        'address': 'Челябинская область, г. Челябинск',
        'area': '13351 +/-40',
        'owner': 'Левин Дмитрий Олегович',
        'permitted_use': '(6.0) производственная деятельность',
        'cadastral_cost': '13050468.99',
        'land_category': 'Земли населенных пунктов',
        'rental_data': {
            'rent_type': 'Аренда',
            'period_start': '02.09.2025',
            'period_end': '31.12.2040',
            'tenant': 'ООО "УК ТЕХНОПАРК ЛД"'
        }
    }
    
    row = create_row_from_extracted_data(test_data, "test.pdf", 1)
    df = add_row_to_dataframe(df, row)
    print(f"   ✓ Строка добавлена\n")
    
    # 3. Добавить строку ошибки
    print("3️⃣ Добавление строки ошибки...")
    error_row = create_error_row("error.pdf", "Не удалось прочитать файл", 2)
    df = add_row_to_dataframe(df, error_row)
    print(f"   ✓ Строка ошибки добавлена\n")
    
    # 4. Информация о таблице
    print("4️⃣ Информация о таблице:")
    info = get_dataframe_info(df)
    for key, value in info.items():
        if key != 'columns':
            print(f"   {key}: {value}")
    
    # 5. Проверка таблицы
    print(f"\n5️⃣ Проверка таблицы...")
    is_valid = validate_dataframe(df)
    print(f"   Таблица корректна: {is_valid}\n")
    
    # 6. Заполнить номера
    print("6️⃣ Заполнение номеров п/п...")
    df = fill_numbers_column(df)
    print(f"   ✓ Номера заполнены\n")
    
    # 7. Вывести таблицу
    print("7️⃣ Таблица:\n")
    print(df.to_string())
    
    print("\n✅ Тестирование завершено!")