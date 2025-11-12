# -*- coding: utf-8 -*-
"""
pdf_parser_v2.py
----------------
УЛУЧШЕННЫЙ модуль для чтения PDF файлов.
Поддерживает: обычные PDF, защищенные PDF, сканированные PDF (OCR).
"""

import re
from pathlib import Path
from typing import Optional, List, Dict
import sys

# Импортируем библиотеки для работы с PDF
try:
    import pdfplumber
    PDF_LIBRARY = "pdfplumber"
except ImportError:
    try:
        from pypdf import PdfReader
        PDF_LIBRARY = "pypdf"
    except ImportError:
        PDF_LIBRARY = None

# Импортируем для OCR (если доступно)
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from logger_cfg import setup_logger
from settings import MAX_PDF_SIZE_MB, VALID_EXTENSIONS

# ════════════════════════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ
# ════════════════════════════════════════════════════════════════════════════

logger = setup_logger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАЩИЩЕННЫМИ И СКАНИРОВАННЫМИ PDF
# ════════════════════════════════════════════════════════════════════════════

def is_pdf_scanned_or_protected(file_path: str) -> bool:
    """
    Проверяет, является ли PDF сканированным или защищенным.
    
    Args:
        file_path: Путь к PDF файлу
        
    Returns:
        bool: True если PDF сканированный или защищен
    """
    try:
        if PDF_LIBRARY == "pdfplumber":
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages[:1]:  # Проверяем первую страницу
                    text = page.extract_text()
                    if not text or len(text.strip()) < 10:
                        logger.warning(f"PDF похож на сканированный или защищенный (мало текста: {len(text or '')} символов)")
                        return True
        return False
    except Exception as e:
        logger.warning(f"Ошибка при проверке PDF: {e}")
        return False


def extract_text_with_table_detection(file_path: str) -> Optional[str]:
    """
    Извлекает текст из PDF с поддержкой таблиц (pdfplumber).
    
    Args:
        file_path: Путь к PDF файлу
        
    Returns:
        str: Извлеченный текст или None
    """
    try:
        logger.info("Попытка извлечения с использованием pdfplumber (с поддержкой таблиц)...")
        
        full_text = []
        text_count = 0
        
        with pdfplumber.open(file_path) as pdf:
            logger.debug(f"PDF содержит {len(pdf.pages)} страниц")
            
            for page_num, page in enumerate(pdf.pages, 1):
                # 1. Попробуем извлечь основной текст
                page_text = page.extract_text() or ""
                text_count += len(page_text.strip())
                
                # 2. Если текст не найден, пробуем извлечь текст из таблиц
                if len(page_text.strip()) < 5:
                    logger.debug(f"Страница {page_num}: мало основного текста, пробуем таблицы...")
                    
                    tables = page.extract_tables()
                    if tables:
                        table_text = "\n".join([
                            " | ".join([str(cell) for cell in row if cell])
                            for table in tables
                            for row in table
                        ])
                        page_text += "\n" + table_text
                        logger.debug(f"Страница {page_num}: найдено {len(tables)} таблиц")
                
                # 3. Если всё ещё мало текста, пробуем извлечь из других элементов
                if len(page_text.strip()) < 5:
                    logger.debug(f"Страница {page_num}: пробуем извлечь из объектов...")
                    # Получим любой доступный текст
                    if hasattr(page, 'chars') and page.chars:
                        char_text = "".join([c.get('text', '') for c in page.chars])
                        page_text += char_text
                
                full_text.append(page_text)
                logger.debug(f"Страница {page_num}: {len(page_text.strip())} символов")
        
        result_text = "\n".join(full_text)
        
        if text_count < 50:
            logger.warning(f"⚠️ ВНИМАНИЕ: Извлечено очень мало текста ({text_count} символов)")
            logger.warning("PDF может быть сканированным или защищенным!")
            logger.warning("Рекомендуется использовать OCR или конвертировать PDF")
            return result_text if result_text.strip() else None
        
        logger.info(f"✓ Извлечено {len(result_text)} символов ({text_count} значащих)")
        return result_text
        
    except Exception as e:
        logger.error(f"Ошибка pdfplumber: {type(e).__name__}: {str(e)}")
        return None


def extract_text_from_pdf_images(file_path: str) -> Optional[str]:
    """
    Извлекает текст из PDF конвертируя страницы в изображения (для сканированных PDF).
    ТРЕБУЕТ: pdf2image, pytesseract, pillow
    
    Args:
        file_path: Путь к PDF файлу
        
    Returns:
        str: Извлеченный текст или None
    """
    try:
        logger.info("Попытка OCR обработки PDF...")
        
        # Пробуем импортировать необходимые библиотеки
        try:
            from pdf2image import convert_from_path
        except ImportError:
            logger.error("Требуется установка: pip install pdf2image pillow pytesseract")
            logger.error("Также требуется установка Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
            return None
        
        if not OCR_AVAILABLE:
            logger.error("Требуется установка: pip install pytesseract pillow")
            return None
        
        logger.debug("Конвертирование PDF в изображения...")
        images = convert_from_path(file_path)
        
        full_text = []
        for page_num, image in enumerate(images, 1):
            logger.debug(f"OCR обработка страницы {page_num}/{len(images)}...")
            
            try:
                # Используем pytesseract для OCR
                page_text = pytesseract.image_to_string(image, lang='rus+eng')
                full_text.append(page_text)
                logger.debug(f"Страница {page_num}: {len(page_text)} символов")
            except Exception as e:
                logger.warning(f"Ошибка OCR на странице {page_num}: {e}")
        
        result_text = "\n".join(full_text)
        logger.info(f"✓ OCR обработка завершена: {len(result_text)} символов")
        
        return result_text if result_text.strip() else None
        
    except Exception as e:
        logger.error(f"Ошибка OCR: {type(e).__name__}: {str(e)}")
        return None


def validate_pdf_file(file_path: str) -> bool:
    """Проверяет валидность PDF файла."""
    path = Path(file_path)
    
    if not path.exists():
        logger.error(f"Файл не найден: {file_path}")
        return False
    
    if path.suffix.lower() not in VALID_EXTENSIONS:
        logger.error(f"Неверное расширение: {path.suffix}")
        return False
    
    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_PDF_SIZE_MB:
        logger.error(f"Файл слишком большой: {file_size_mb:.2f} MB")
        return False
    
    return True


def extract_text_from_pdf(file_path: str, try_ocr: bool = False) -> Optional[str]:
    """
    ГЛАВНАЯ ФУНКЦИЯ: Извлекает текст из PDF.
    
    Args:
        file_path: Путь к PDF файлу
        try_ocr: Использовать ли OCR если текст не извлекается (требует установки)
        
    Returns:
        str: Извлеченный текст или None
        
    Алгоритм:
    1. Валидирует файл
    2. Пробует pdfplumber (с таблицами)
    3. Если мало текста, пробует PyPDF
    4. Если всё ещё мало, пробует OCR (если try_ocr=True)
    """
    
    if not validate_pdf_file(file_path):
        return None
    
    logger.info(f"Начало извлечения текста из: {Path(file_path).name}")
    
    # Попытка 1: pdfplumber (приоритет - хорошо работает с таблицами)
    if PDF_LIBRARY == "pdfplumber" or PDF_LIBRARY is None:
        text = extract_text_with_table_detection(file_path)
        if text and len(text.strip()) > 50:
            return text
    
    # Попытка 2: PyPDF (резервный)
    if PDF_LIBRARY == "pypdf" or (PDF_LIBRARY is None and not text):
        logger.info("Попытка использовать PyPDF...")
        try:
            from pypdf import PdfReader
            full_text = []
            
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text() or ""
                    full_text.append(page_text)
                    logger.debug(f"Страница {page_num}: {len(page_text.strip())} символов")
            
            text = "\n".join(full_text)
            if text and len(text.strip()) > 50:
                return text
        except Exception as e:
            logger.error(f"Ошибка PyPDF: {e}")
    
    # Попытка 3: OCR для сканированных PDF
    if try_ocr and (not text or len(text.strip()) < 50):
        logger.warning("⚠️ Текст не извлечен. Пробуем OCR для сканированного PDF...")
        text = extract_text_from_pdf_images(file_path)
        if text:
            return text
    
    # Если всё равно ничего не получилось
    if not text or len(text.strip()) < 5:
        logger.error("✗ Не удалось извлечь текст из PDF")
        logger.error("Возможные причины:")
        logger.error("  1. PDF является сканированным изображением (требуется OCR)")
        logger.error("  2. PDF защищен от копирования текста")
        logger.error("  3. PDF повреждена")
        logger.error("\nРешения:")
        logger.error("  1. Установить tesseract: pip install pytesseract pdf2image")
        logger.error("  2. Установить Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
        logger.error("  3. Использовать extract_text_from_pdf(..., try_ocr=True)")
        return None
    
    logger.info(f"✓ Извлечено {len(text)} символов")
    return text


def get_pdf_metadata(file_path: str) -> Optional[Dict]:
    """Получает метаданные PDF файла."""
    if not validate_pdf_file(file_path):
        return None
    
    try:
        path = Path(file_path)
        metadata = {
            'file_name': path.name,
            'file_path': str(path.absolute()),
            'file_size_kb': path.stat().st_size / 1024,
        }
        
        if PDF_LIBRARY == "pdfplumber":
            with pdfplumber.open(file_path) as pdf:
                metadata['num_pages'] = len(pdf.pages)
        else:
            from pypdf import PdfReader
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                metadata['num_pages'] = len(pdf_reader.pages)
        
        return metadata
        
    except Exception as e:
        logger.error(f"Ошибка при получении метаданных: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════
# ТЕСТИРОВАНИЕ
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🧪 Тестирование УЛУЧШЕННОГО модуля pdf_parser_v2.py\n")
    
    test_pdf = "data/input/Здание №1 - 425 УК Технопарк ЛД.pdf"
    
    if Path(test_pdf).exists():
        print(f"📄 Тестирование файла: {test_pdf}\n")
        
        # Метаданные
        metadata = get_pdf_metadata(test_pdf)
        if metadata:
            print(f"📊 Метаданные:")
            for key, value in metadata.items():
                print(f"   {key}: {value}")
        
        # Проверка
        is_scanned = is_pdf_scanned_or_protected(test_pdf)
        print(f"\n📋 PDF статус:")
        print(f"   Сканированный/защищенный: {is_scanned}")
        
        # Извлечение текста БЕЗ OCR
        print(f"\n📝 Попытка 1: Извлечение БЕЗ OCR...\n")
        text = extract_text_from_pdf(test_pdf, try_ocr=False)
        
        if text and len(text.strip()) > 50:
            print(f"✅ УСПЕХ!\n")
            print(f"Первые 500 символов:\n")
            print(text[:500])
            print(f"\n... (всего {len(text)} символов)")
        else:
            print(f"⚠️ МАЛО ТЕКСТА (всего {len(text or '') if text else 0} символов)")
            print(f"\n📝 Попытка 2: Можно ли использовать OCR?")
            print(f"   OCR доступен: {OCR_AVAILABLE}")
            
            if OCR_AVAILABLE:
                print(f"\n💡 Рекомендация: Используйте extract_text_from_pdf(..., try_ocr=True)")
            else:
                print(f"\n💡 Требуется установка:")
                print(f"   pip install pytesseract pdf2image pillow")
                print(f"   И Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
    else:
        print(f"❌ Файл не найден: {test_pdf}")