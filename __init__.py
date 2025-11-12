# -*- coding: utf-8 -*-
"""
__init__.py (корневой)
---------------------
Точка входа пакета PDF Parser EGРN.
Экспортирует основные классы и функции для использования в других модулях.
"""

__version__ = "1.0.0"
__author__ = "PDF Parser Team"
__description__ = "Извлечение данных из выписок ЕГРН в Excel"

# Импортируем основные компоненты для удобного доступа
from src.logger_cfg import (
    setup_logger,
    get_main_logger,
    log_file_processing_started,
    log_file_processing_success,
    log_file_processing_error,
    log_extraction_warning,
    log_summary,
)

from src.settings import (
    PROJECT_ROOT,
    INPUT_DIR,
    OUTPUT_DIR,
    LOGS_DIR,
    EXCEL_COLUMNS,
    REGEX_PATTERNS,
    PDF_SEARCH_PATTERNS,
    MESSAGES,
    ERROR_HANDLING,
)

# Версия проекта
__all__ = [
    # Логирование
    'setup_logger',
    'get_main_logger',
    'log_file_processing_started',
    'log_file_processing_success',
    'log_file_processing_error',
    'log_extraction_warning',
    'log_summary',
    
    # Конфигурация
    'PROJECT_ROOT',
    'INPUT_DIR',
    'OUTPUT_DIR',
    'LOGS_DIR',
    'EXCEL_COLUMNS',
    'REGEX_PATTERNS',
    'PDF_SEARCH_PATTERNS',
    'MESSAGES',
    'ERROR_HANDLING',
    
    # Информация о пакете
    '__version__',
    '__author__',
    '__description__',
]

# Вывести информацию при импорте (для отладки)
if __name__ != '__main__':
    _logger = get_main_logger()
    _logger.debug(f"PDF Parser EGРN v{__version__} инициализирован")