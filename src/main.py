# -*- coding: utf-8 -*-
"""
main.py
-------
ГЛАВНЫЙ СКРИПТ интеграции всех компонентов проекта PDF Parser EGРN.

Функциональность:
- Сканирует папку data/input/ на наличие PDF файлов
- Для каждого PDF: читает текст, парсит данные, создает строку таблицы
- Обрабатывает ошибки парсинга (создает пустые строки)
- Сохраняет итоговый Excel файл в data/output/
- Выводит подробную статистику и отчет
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import time

# Импортируем все модули проекта
from logger_cfg import setup_logger, log_file_processing_started, log_file_processing_success, log_file_processing_error, log_summary
from settings import INPUT_DIR, LOGS_DIR, OUTPUT_DIR, MESSAGES
from pdf_parser import extract_text_from_pdf, get_pdf_metadata
from data_extractor import extract_all_data
from table_builder import (
    create_empty_dataframe,
    create_row_from_extracted_data,
    create_error_row,
    add_rows_batch,
    fill_numbers_column,
    get_dataframe_info,
)
from excel_writer import save_dataframe_to_excel, get_file_size

# ════════════════════════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ
# ════════════════════════════════════════════════════════════════════════════

logger = setup_logger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# ОСНОВНЫЕ ФУНКЦИИ
# ════════════════════════════════════════════════════════════════════════════

def print_welcome_message():
    """Выводит приветственное сообщение."""
    print(MESSAGES['welcome'])


def find_pdf_files(search_path: Path) -> List[Path]:
    """
    Ищет все PDF файлы в папке.
    
    Args:
        search_path: Папка для поиска
        
    Returns:
        List[Path]: Список найденных PDF файлов
    """
    
    if not search_path.exists():
        logger.error(f"Папка не существует: {search_path}")
        return []
    
    pdf_files = list(search_path.glob("*.pdf")) + list(search_path.glob("*.PDF"))
    
    if not pdf_files:
        logger.warning(f"Не найдено PDF файлов в {search_path}")
        return []
    
    return sorted(pdf_files)


def process_single_pdf(
    pdf_path: Path,
    row_number: int
) -> Tuple[bool, Dict]:
    """
    Обрабатывает один PDF файл.
    
    Args:
        pdf_path: Путь к PDF файлу
        row_number: Номер строки в таблице
        
    Returns:
        Tuple[bool, Dict]: (успех, словарь со строкой таблицы)
    """
    
    pdf_name = pdf_path.name
    
    try:
        # Логируем начало обработки
        metadata = get_pdf_metadata(str(pdf_path))
        log_file_processing_started(logger, pdf_name, metadata['num_pages'] if metadata else 0, row_number)
        
        # Читаем PDF с поддержкой OCR
        text = extract_text_from_pdf(str(pdf_path), try_ocr=True)
        
        if not text or len(text.strip()) < 20:
            logger.warning(f"Не удалось извлечь текст из {pdf_name}")
            error_row = create_error_row(pdf_name, "Не удалось извлечь текст из PDF", row_number)
            log_file_processing_error(logger, pdf_name, "Текст не извлечен")
            return False, error_row
        
        # Парсим данные
        data = extract_all_data(text)
        
        # Проверяем, что хотя бы кадастровый номер найден
        if not data.get('cadastral_number'):
            logger.warning(f"Кадастровый номер не найден в {pdf_name}")
            # Но всё равно создаем строку с найденными данными
        
        # Создаем строку таблицы
        row = create_row_from_extracted_data(data, pdf_name, row_number)
        
        # Логируем успех
        log_file_processing_success(
            logger,
            pdf_name,
            data.get('cadastral_number') or 'не найден',
            data.get('address') or 'не найден'
        )
        
        return True, row
        
    except Exception as e:
        logger.error(f"Ошибка при обработке {pdf_name}: {type(e).__name__}: {str(e)}")
        error_row = create_error_row(pdf_name, str(e), row_number)
        log_file_processing_error(logger, pdf_name, str(e))
        return False, error_row


def process_all_pdfs(pdf_files: List[Path]) -> Dict:
    """
    Обрабатывает все PDF файлы.
    
    Args:
        pdf_files: Список PDF файлов
        
    Returns:
        Dict: Статистика обработки
    """
    
    logger.info(f"Начало обработки {len(pdf_files)} PDF файлов")
    
    # Инициализируем статистику
    stats = {
        'total_files': len(pdf_files),
        'successful': 0,
        'failed': 0,
        'rows': [],
        'processing_time': 0,
    }
    
    start_time = time.time()
    
    # Обрабатываем каждый файл
    for idx, pdf_file in enumerate(pdf_files, 1):
        success, row = process_single_pdf(pdf_file, idx)
        
        stats['rows'].append(row)
        
        if success:
            stats['successful'] += 1
        else:
            stats['failed'] += 1
        
        # Выводим прогресс
        status_symbol = "✓" if success else "✗"
        print(f"[{idx}/{len(pdf_files)}] {status_symbol} {pdf_file.name}")
    
    stats['processing_time'] = time.time() - start_time
    
    logger.info(f"Обработка завершена за {stats['processing_time']:.2f} сек")
    
    return stats


def create_final_dataframe(rows: List[Dict]) -> any:
    """
    Создает финальный DataFrame из всех строк.
    
    Args:
        rows: Список строк
        
    Returns:
        pd.DataFrame: Финальная таблица
    """
    
    logger.debug(f"Создание финального DataFrame из {len(rows)} строк")
    
    # Создаем пустую таблицу
    df = create_empty_dataframe()
    
    # Добавляем все строки
    if rows:
        df = add_rows_batch(df, rows)
    
    # Заполняем номера п/п
    df = fill_numbers_column(df)
    
    return df


def print_final_report(stats: Dict, output_file: str):
    """
    Выводит финальный отчет.
    
    Args:
        stats: Статистика обработки
        output_file: Путь к выходному Excel файлу
    """
    
    print(f"\n{MESSAGES['summary_header']}")
    print(MESSAGES['summary_total'].format(stats['total_files']))
    print(MESSAGES['summary_rows'].format(stats['successful']))
    print(MESSAGES['summary_errors'].format(stats['failed']))
    
    if output_file:
        file_size = get_file_size(output_file)
        print(MESSAGES['summary_excel'].format(output_file))
        print(f"   Размер: {file_size}")
    
    print(MESSAGES['summary_logs'].format(LOGS_DIR))
    print(f"   Время обработки: {stats['processing_time']:.2f} сек")
    print(f"{MESSAGES['summary_header']}\n")


def main():
    """ГЛАВНАЯ ФУНКЦИЯ - интеграция всех компонентов."""
    
    # 1. Приветствие
    print_welcome_message()
    
    # 2. Поиск PDF файлов
    print(f"🔍 Поиск PDF файлов в: {INPUT_DIR}\n")
    pdf_files = find_pdf_files(INPUT_DIR)
    
    if not pdf_files:
        print(MESSAGES['no_pdf_files'].format(INPUT_DIR))
        return
    
    print(MESSAGES['pdf_files_found'].format(len(pdf_files)))
    for i, pdf in enumerate(pdf_files, 1):
        print(f"   {i}. {pdf.name}")
    
    # 3. Обработка PDF файлов
    print(f"\n{MESSAGES['processing']}\n")
    stats = process_all_pdfs(pdf_files)
    
    # 4. Создание таблицы
    print(f"\n📋 Создание итоговой таблицы...")
    df = create_final_dataframe(stats['rows'])
    
    info = get_dataframe_info(df)
    print(f"   ✓ Таблица создана: {info['total_rows']} строк, {info['total_columns']} колонок")
    
    # 5. Сохранение Excel
    print(f"\n📊 Сохранение Excel файла...")
    output_file = save_dataframe_to_excel(df)
    print(f"   ✓ {output_file}")
    
    # 6. Финальный отчет
    print_final_report(stats, output_file if output_file else None)
    
    # 7. Логирование итогов
    log_summary(logger, stats['successful'], stats['failed'], stats['total_files'], 
           output_file if output_file else "Не создан")


# ════════════════════════════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Обработка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {type(e).__name__}: {str(e)}")
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)