# -*- coding: utf-8 -*-
"""
logger_config.py
----------------
Конфигурация и инициализация системы логирования.
Предоставляет логгеры для различных модулей приложения.
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from settings import (
    LOGS_DIR,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_FILE_PREFIX,
    LOG_MAX_SIZE,
    LOG_BACKUP_COUNT,
)

# ============================================================================
# ГЛОБАЛЬНЫЕ ЛОГГЕРЫ
# ============================================================================

def setup_logger(name: str, log_file_name: str = None) -> logging.Logger:
    """
    Инициализирует и возвращает логгер с ротацией файлов.
    
    Args:
        name: Имя логгера (обычно __name__ модуля)
        log_file_name: Имя файла логов (опционально)
        
    Returns:
        logging.Logger: Настроенный логгер
        
    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Это информационное сообщение")
        >>> logger.error("Это ошибка")
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # Проверяем, не были ли уже добавлены обработчики
    if logger.hasHandlers():
        return logger
    
    # Создаем папку для логов, если её нет
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Определяем имя файла логов
    if log_file_name is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file_name = f"{LOG_FILE_PREFIX}_{timestamp}.log"
    
    log_file_path = LOGS_DIR / log_file_name
    
    # ========================================================================
    # ОБРАБОТЧИК 1: Файл с ротацией
    # ========================================================================
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file_path,
        maxBytes=LOG_MAX_SIZE,  # 10 MB
        backupCount=LOG_BACKUP_COUNT,  # Хранить 5 резервных копий
        encoding='utf-8',
    )
    file_handler.setLevel(LOG_LEVEL)
    
    # Форматер для файла (подробный)
    file_formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # ========================================================================
    # ОБРАБОТЧИК 2: Консоль (потому что интерфейс консольный)
    # ========================================================================
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # В консоль только WARNING и выше
    
    # Форматер для консоли (компактный)
    console_formatter = logging.Formatter(
        fmt="%(levelname)-8s | %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


# ============================================================================
# СПЕЦИАЛИЗИРОВАННЫЕ ФУНКЦИИ ЛОГИРОВАНИЯ
# ============================================================================

def log_file_processing_started(logger: logging.Logger, file_name: str, total_files: int, current_index: int):
    """Логирует начало обработки файла"""
    logger.info(f"[{current_index}/{total_files}] Начало обработки файла: {file_name}")


def log_file_processing_success(logger, pdf_name, cadastral_number=None, address=None):
    logger.info(f"✓ Успешно: {pdf_name}")
    if cadastral_number:
        logger.debug(f"  Кадастр. номер: {cadastral_number}")
    if address:
        logger.debug(f"  Адрес: {address}")


def log_file_processing_error(logger: logging.Logger, file_name: str, error: Exception):
    """Логирует ошибку при обработке файла"""
    logger.error(
        f"✗ Ошибка при обработке {file_name}: {type(error).__name__}: {str(error)}",
        exc_info=False
    )


def log_extraction_warning(logger: logging.Logger, file_name: str, field_name: str, reason: str = "не найдено"):
    """Логирует предупреждение об отсутствии поля"""
    logger.warning(
        f"Файл '{file_name}': поле '{field_name}' {reason}"
    )


def log_summary(logger, successful, failed, total, excel_file=None):
    logger.info(f"=== ИТОГИ ОБРАБОТКИ ===")
    logger.info(f"Всего файлов: {total}")
    logger.info(f"Успешно: {successful}")
    logger.info(f"Ошибок: {failed}")
    if excel_file:
        logger.info(f"Excel файл: {excel_file}")


# ============================================================================
# ИНИЦИАЛИЗАЦИЯ ОСНОВНОГО ЛОГГЕРА
# ============================================================================

# Этот логгер используется по умолчанию в других модулях
def get_main_logger() -> logging.Logger:
    """
    Возвращает основной логгер приложения.
    
    Returns:
        logging.Logger: Основной логгер
        
    Example:
        >>> logger = get_main_logger()
    """
    return setup_logger("pdf_parser_main")


# Кэшируем основной логгер
_main_logger = get_main_logger()


def main_logger() -> logging.Logger:
    """Быстрый доступ к основному логгеру"""
    return _main_logger


# ============================================================================
# ТЕСТИРОВАНИЕ
# ============================================================================

if __name__ == "__main__":
    # Пример использования логгера
    print("🧪 Тестирование системы логирования...\n")
    
    test_logger = setup_logger("test_module", "test_log.log")
    
    # Различные уровни логирования
    test_logger.debug("📌 Это DEBUG сообщение (в файл)")
    test_logger.info("ℹ️  Это INFO сообщение")
    test_logger.warning("⚠️  Это WARNING сообщение (видно в консоли и файле)")
    test_logger.error("❌ Это ERROR сообщение (видно везде)")
    
    # Специальные функции
    test_logger.info("")
    print("Используем специальные функции логирования:\n")
    
    log_file_processing_started(test_logger, "example.pdf", 5, 1)
    log_file_processing_success(test_logger, "example.pdf", "74:36:0303005:454")
    log_extraction_warning(test_logger, "another.pdf", "Площадь", "не найдено")
    log_summary(test_logger, 5, 4, 1, "/path/to/output.xlsx")
    
    print("\n✅ Логирование инициализировано успешно!")
    print(f"📁 Логи сохраняются в: {LOGS_DIR}")