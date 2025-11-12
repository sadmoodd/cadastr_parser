# -*- coding: utf-8 -*-
"""
data_extractor.py
-----------------
Модуль для парсинга и извлечения данных из текста PDF.
Использует регулярные выражения из settings.py для поиска нужных полей.
"""

import re
from typing import Optional, Dict, List, Tuple
from pathlib import Path

from logger_cfg import setup_logger
from settings import (
    REGEX_PATTERNS,
    PDF_SEARCH_PATTERNS,
    EMPTY_DATA_MARKERS,
)

# ════════════════════════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ
# ════════════════════════════════════════════════════════════════════════════

logger = setup_logger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ════════════════════════════════════════════════════════════════════════════

def clean_text(text: Optional[str]) -> str:
    """
    Очищает и нормализирует извлеченный текст.
    
    Args:
        text: Исходный текст
        
    Returns:
        str: Очищенный текст
        
    Операции:
    - Удаляет лишние пробелы
    - Удаляет символы новой строки в конце
    - Нормализирует пробелы
    """
    if not text:
        return ""
    
    # Удаляем лишние пробелы и переносы строк
    text = text.strip()
    # Нормализируем пробелы (несколько пробелов -> один)
    text = re.sub(r'\s+', ' ', text)
    
    return text


def is_empty_marker(text: str) -> bool:
    """
    Проверяет, является ли текст маркером отсутствия данных.
    
    Args:
        text: Текст для проверки
        
    Returns:
        bool: True если это маркер отсутствия, False иначе
    """
    if not text:
        return True
    
    clean = text.strip().lower()
    return clean in [m.lower() for m in EMPTY_DATA_MARKERS]


# ════════════════════════════════════════════════════════════════════════════
# ГЛАВНЫЕ ФУНКЦИИ ИЗВЛЕЧЕНИЯ
# ════════════════════════════════════════════════════════════════════════════

def extract_cadastral_number(text: str) -> Optional[str]:
    """
    Извлекает кадастровый номер (XX:XX:XXXXXXX:XXX).
    
    Args:
        text: Текст из PDF
        
    Returns:
        str: Кадастровый номер (например: 74:36:0303005:454) или None
    """
    if not text:
        return None
    
    pattern = REGEX_PATTERNS.get('cadastral_number')
    match = re.search(pattern, text)
    
    if match:
        result = match.group(1)
        logger.debug(f"Найден кадастровый номер: {result}")
        return result
    
    logger.warning("Кадастровый номер не найден")
    return None


def extract_area(text: str) -> Optional[str]:
    """
    Извлекает площадь в м² (может быть с ошибкой вида 13351 +/-40).
    
    Args:
        text: Текст из PDF
        
    Returns:
        str: Площадь (например: 13351 +/-40) или None
    """
    if not text:
        return None
    
    pattern = REGEX_PATTERNS.get('area')
    match = re.search(pattern, text)
    
    if match:
        result = match.group(1).strip()
        logger.debug(f"Найдена площадь: {result}")
        return result
    
    logger.debug("Площадь не найдена")
    return None


def extract_address(text: str) -> Optional[str]:
    """
    Извлекает адрес (может быть многострочный).
    
    Args:
        text: Текст из PDF
        
    Returns:
        str: Полный адрес или None
    """
    if not text:
        return None
    
    pattern = REGEX_PATTERNS.get('address')
    match = re.search(pattern, text)
    
    if match:
        result = clean_text(match.group(1))
        logger.debug(f"Найден адрес: {result[:50]}...")
        return result
    
    logger.debug("Адрес не найден")
    return None


def extract_owner(text: str) -> Optional[str]:
    """
    Извлекает правообладателя (ФИО собственника).
    
    Args:
        text: Текст из PDF
        
    Returns:
        str: ФИО собственника или None
    """
    if not text:
        return None
    
    pattern = REGEX_PATTERNS.get('owner')
    match = re.search(pattern, text)
    
    if match:
        result = clean_text(match.group(1))
        logger.debug(f"Найден собственник: {result}")
        return result
    
    logger.debug("Собственник не найден")
    return None


def extract_rental_info(text: str) -> Optional[Dict[str, str]]:
    """
    Извлекает информацию об аренде (вид, период, арендатор).
    
    Args:
        text: Текст из PDF
        
    Returns:
        Dict: {'rent_type': ..., 'period_start': ..., 'period_end': ..., 'tenant': ...}
              или None если информация об аренде не найдена
    """
    if not text:
        return None
    
    rental_data = {}
    
    # 1. Тип обременения (обычно "Аренда")
    pattern = REGEX_PATTERNS.get('rent_type')
    match = re.search(pattern, text)
    if match:
        rental_data['rent_type'] = clean_text(match.group(1))
    
    # 2. Период аренды (2 даты!)
    pattern = REGEX_PATTERNS.get('rental_period')
    match = re.search(pattern, text)
    if match:
        rental_data['period_start'] = match.group(1)
        rental_data['period_end'] = match.group(2)
        logger.debug(f"Период аренды: {rental_data['period_start']} - {rental_data['period_end']}")
    
    # 3. Арендатор (организация)
    pattern = REGEX_PATTERNS.get('tenant')
    match = re.search(pattern, text)
    if match:
        rental_data['tenant'] = clean_text(match.group(1))
        logger.debug(f"Арендатор: {rental_data['tenant'][:50]}...")
    
    return rental_data if rental_data else None


def extract_permitted_use(text: str) -> Optional[str]:
    """
    Извлекает виды разрешенного использования.
    
    Args:
        text: Текст из PDF
        
    Returns:
        str: Виды использования или None
    """
    if not text:
        return None
    
    pattern = REGEX_PATTERNS.get('permitted_use')
    match = re.search(pattern, text)
    
    if match:
        result = clean_text(match.group(1))
        logger.debug(f"Найдены виды использования: {result[:50]}...")
        return result
    
    logger.debug("Виды использования не найдены")
    return None


def extract_cadastral_cost(text: str) -> Optional[str]:
    """
    Извлекает кадастровую стоимость в рублях.
    
    Args:
        text: Текст из PDF
        
    Returns:
        str: Стоимость (например: 13050468.99) или None
    """
    if not text:
        return None
    
    pattern = REGEX_PATTERNS.get('cadastral_cost')
    match = re.search(pattern, text)
    
    if match:
        result = clean_text(match.group(1))
        logger.debug(f"Найдена кадастровая стоимость: {result}")
        return result
    
    logger.debug("Кадастровая стоимость не найдена")
    return None


def extract_land_category(text: str) -> Optional[str]:
    """
    Извлекает категорию земель.
    
    Args:
        text: Текст из PDF
        
    Returns:
        str: Категория земель или None
    """
    if not text:
        return None
    
    pattern = REGEX_PATTERNS.get('land_category')
    match = re.search(pattern, text)
    
    if match:
        result = clean_text(match.group(1))
        logger.debug(f"Найдена категория земель: {result}")
        return result
    
    logger.debug("Категория земель не найдена")
    return None


# ════════════════════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ: РАСПАРСИТЬ ВСЕ ДАННЫЕ
# ════════════════════════════════════════════════════════════════════════════

def extract_all_data(text: str) -> Dict[str, Optional[str]]:
    """
    Главная функция: распарсит ВСЕ данные из текста PDF.
    
    Args:
        text: Весь текст из PDF файла
        
    Returns:
        Dict: Словарь со всеми извлеченными полями
        
    Возвращаемые ключи:
    - cadastral_number: Кадастровый номер
    - address: Адрес
    - area: Площадь
    - owner: Собственник
    - permitted_use: Виды использования
    - cadastral_cost: Кадастровая стоимость
    - land_category: Категория земель
    - rental_data: Информация об аренде (словарь)
    
    Структура:
    {
        'cadastral_number': '74:36:0303005:454',
        'address': 'Челябинская область, г. Челябинск...',
        'area': '13351 +/-40',
        'owner': 'Левин Дмитрий Олегович',
        'permitted_use': '(6.0) производственная деятельность...',
        'cadastral_cost': '13050468.99',
        'land_category': 'Земли населенных пунктов',
        'rental_data': {
            'rent_type': 'Аренда',
            'period_start': '02.09.2025',
            'period_end': '31.12.2040',
            'tenant': 'ООО "УК ТЕХНОПАРК ЛД"'
        }
    }
    """
    
    logger.info("Начало парсинга всех данных из текста")
    
    # Инициализируем словарь
    data = {
        'cadastral_number': None,
        'address': None,
        'area': None,
        'owner': None,
        'permitted_use': None,
        'cadastral_cost': None,
        'land_category': None,
        'rental_data': None,
    }
    
    # Извлекаем каждое поле
    data['cadastral_number'] = extract_cadastral_number(text)
    data['address'] = extract_address(text)
    data['area'] = extract_area(text)
    data['owner'] = extract_owner(text)
    data['permitted_use'] = extract_permitted_use(text)
    data['cadastral_cost'] = extract_cadastral_cost(text)
    data['land_category'] = extract_land_category(text)
    data['rental_data'] = extract_rental_info(text)
    
    # Логирование результатов
    found_count = sum(1 for v in data.values() if v is not None)
    logger.info(f"Успешно извлечено {found_count} полей из 8")
    
    return data


# ════════════════════════════════════════════════════════════════════════════
# ТЕСТИРОВАНИЕ
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from pdf_parser import extract_text_from_pdf
    
    print("🧪 Тестирование модуля data_extractor.py\n")
    
    # Пример с вашим PDF файлом
    test_pdf = "data/input/Здание №1 - 425 УК Технопарк ЛД.pdf"
    
    if Path(test_pdf).exists():
        print(f"📄 Тестирование файла: {test_pdf}\n")
        
        # Извлечь текст
        print("📝 Этап 1: Чтение PDF...")
        text = extract_text_from_pdf(test_pdf)
        
        if text:
            print("✅ PDF успешно прочитан!\n")
            
            # Распарсить данные
            print("🔍 Этап 2: Парсинг данных...\n")
            data = extract_all_data(text)
            
            # Вывести результаты
            print("📊 РЕЗУЛЬТАТЫ ПАРСИНГА:\n")
            for key, value in data.items():
                if key == 'rental_data' and value:
                    print(f"{key}:")
                    for rent_key, rent_value in value.items():
                        print(f"  └─ {rent_key}: {rent_value}")
                else:
                    print(f"{key}: {value}")
            
            print("\n✅ Тестирование завершено!")
        else:
            print("❌ Не удалось прочитать PDF")
    else:
        print(f"❌ Файл не найден: {test_pdf}")
        print(f"📍 Поместите PDF в текущую папку для тестирования")