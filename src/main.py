# -*- coding: utf-8 -*-
"""
main.py
----------------
ГЛАВНЫЙ СКРИПТ с AI-агентом на базе Qwen3-VL через Hugging Face Router.

Функциональность:
- Интерактивное числовое меню для удобства
- Запрос к Qwen3-VL вместо стандартного OCR
- Обработка PDF файлов с помощью LLM
- Сохранение результатов в Excel
- Краткий отчет о обработке
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
import time
import base64
import json
import requests
import re

from pdf2image import convert_from_path
from PIL import Image
from io import BytesIO

# Импортируем все модули проекта
from logger_cfg import setup_logger
from settings import INPUT_DIR, OUTPUT_DIR, LOGS_DIR, MESSAGES, REGEX_PATTERNS
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
# КОНФИГУРАЦИЯ
# ════════════════════════════════════════════════════════════════════════════

logger = setup_logger(__name__)

# Hugging Face Chat Completions API (Router)
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN env var is not set")
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen3-VL-30B-A3B-Instruct"

# System prompt для модели
SYSTEM_PROMPT = """Ты - специалист по обработке документов ЕГРН (Единый государственный реестр недвижимости).

Твоя задача: Извлечь из предоставленного изображения/документа ЕГРН следующие данные в строгом формате JSON:

{
    "cadastral_number": "XX:XX:XXXXXXX:XXX или null",
    "address": "Полный адрес объекта или null",
    "area": "Площадь в м² или null",
    "owner": "ФИО собственника или название организации или null",
    "permitted_use": "Вид разрешенного использования или null",
    "cadastral_cost": "Кадастровая стоимость в руб или null",
    "land_category": "Категория земель или null",
    "rental_data": {
        "rent_type": "Тип обременения (Аренда/Сервитут/и т.д.) или null",
        "period_start": "Дата начала в формате ДД.ММ.ГГГГ или null",
        "period_end": "Дата конца в формате ДД.ММ.ГГГГ или null",
        "tenant": "Наименование арендатора/организации или null"
    }
}

ПРАВИЛА:
1. Возвращай ТОЛЬКО JSON, без дополнительного текста
2. Используй null для отсутствующих данных, не пропускай ключи
3. Четко следуй структуре JSON
4. Извлекай только информацию, которая явно видна в документе
5. Для кадастрового номера ищи формат: XX:XX:XXXXXXX:XXX
6. Для дат используй формат: ДД.ММ.ГГГГ
7. Не добавляй комментарии или пояснения

Ответ ДОЛЖЕН быть ТОЛЬКО валидный JSON!"""

# ════════════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ PDF/ИЗОБРАЖЕНИЙ
# ════════════════════════════════════════════════════════════════════════════

def pdf_to_images(pdf_path: Path, dpi: int = 150) -> List[Image.Image]:
    """Конвертирует PDF в список PIL.Image."""
    logger.debug(f"Конвертация PDF в изображения: {pdf_path}")
    images = convert_from_path(str(pdf_path), dpi=dpi)
    logger.debug(f"Создано {len(images)} страниц")
    return images


def image_to_base64(image: Image.Image, max_size=(1024, 1024), quality=80) -> str:
    """Конвертирует PIL.Image в base64 JPEG."""
    img = image.copy()
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# ════════════════════════════════════════════════════════════════════════════
# ФУНКЦИИ МЕНЮ
# ════════════════════════════════════════════════════════════════════════════

def print_menu():
    """Выводит главное меню."""
    print("\n" + "=" * 70)
    print("🏛️  PDF PARSER ЕГРN - AI AGENT (Qwen3-VL)")
    print("=" * 70)
    print("\n📋 МЕНЮ:\n")
    print("  1. 🚀 Обработать все PDF из папки по умолчанию")
    print("  2. 📁 Обработать PDF из кастомной папки")
    print("  3. 📊 Показать последний результат")
    print("  4. 🧹 Очистить данные и начать заново")
    print("  5. ❌ Выход\n")
    print("=" * 70)


def get_user_choice() -> int:
    """Получает выбор пользователя."""
    while True:
        try:
            choice = int(input("\n👤 Выберите номер пункта меню (1-5): "))
            if 1 <= choice <= 5:
                return choice
            else:
                print("❌ Пожалуйста, выберите число от 1 до 5")
        except ValueError:
            print("❌ Пожалуйста, введите число")


def get_custom_folder() -> Path:
    """Получает кастомную папку от пользователя."""
    while True:
        folder_path = input("\n📁 Введите путь к папке (или Enter для использования по умолчанию): ").strip()
        if not folder_path:
            return INPUT_DIR

        path = Path(folder_path)
        if path.exists() and path.is_dir():
            return path
        else:
            print(f"❌ Папка не найдена: {folder_path}")

# ════════════════════════════════════════════════════════════════════════════
# ПОСТ-ОБРАБОТКА ДАННЫХ С ПОМОЩЬЮ REGEX_PATTERNS
# ════════════════════════════════════════════════════════════════════════════

def normalize_with_patterns(data: Dict, patterns: Dict) -> Dict:
    """
    Нормализует поля ответа модели с помощью REGEX_PATTERNS,
    не изменяя структуру JSON.
    """
    if not isinstance(data, dict):
        return data

    # Кадастровый номер
    cad_key = "cadastral_number"
    if cad_key in data and isinstance(data[cad_key], str) and data[cad_key]:
        pat = patterns.get("cadastral_number")
        if pat:
            m = re.search(pat, data[cad_key])
            if m:
                data[cad_key] = m.group(0)

    # Площадь
    area_key = "area"
    if area_key in data and isinstance(data[area_key], str) and data[area_key]:
        pat = patterns.get("area")
        if pat:
            m = re.search(pat, data[area_key])
            if m:
                data[area_key] = m.group(0)

    # Кадастровая стоимость
    cost_key = "cadastral_cost"
    if cost_key in data and isinstance(data[cost_key], str) and data[cost_key]:
        pat = patterns.get("cadastral_cost")
        if pat:
            m = re.search(pat, data[cost_key])
            if m:
                data[cost_key] = m.group(0)

    # Даты аренды
    rental = data.get("rental_data")
    if isinstance(rental, dict):
        date_pat = patterns.get("date")
        if date_pat:
            for key in ["period_start", "period_end"]:
                if key in rental and isinstance(rental[key], str) and rental[key]:
                    m = re.search(date_pat, rental[key])
                    if m:
                        rental[key] = m.group(0)

    return data

# ════════════════════════════════════════════════════════════════════════════
# ВЗАИМОДЕЙСТВИЕ С QWEN3-VL ЧЕРЕЗ HF ROUTER
# ════════════════════════════════════════════════════════════════════════════

def query_deepseek_ocr(pdf_path: Path) -> Dict:
    """
    Запрашивает Qwen3-VL через Hugging Face Router для ЕГРН PDF.
    Сейчас обрабатывается только первая страница PDF.
    """
    try:
        logger.debug(f"Запрос к Qwen3-VL для {pdf_path.name}")

        # 1) PDF -> image
        images = pdf_to_images(pdf_path, dpi=300)
        if not images:
            logger.error(f"Не удалось конвертировать PDF в изображения: {pdf_path}")
            return None

        first_page = images[0]
        image_b64 = image_to_base64(first_page)
        image_data_url = f"data:image/jpeg;base64,{image_b64}"

        # 2) Подготовка messages
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Проанализируй этот фрагмент выписки ЕГРН и верни ТОЛЬКО JSON "
                            "в указанном в system-промпте формате."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        },
                    },
                ],
            },
        ]

        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.1,
            "response_format": {
                "type": "json_object"
            },
        }

        response = requests.post(
            HF_API_URL,
            headers=headers,
            json=payload,
            timeout=120,
        )

        if response.status_code != 200:
            logger.error(f"Ошибка API: {response.status_code}")
            logger.error(f"Ответ: {response.text}")
            return None

        data = response.json()

        try:
            result_text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Неожиданная структура ответа: {e}; data={data}")
            return None

        logger.debug(f"Сырой результат от модели: {result_text[:300]}")

        try:
            parsed = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON из ответа модели: {e}")
            return None

        # Пост-обработка с использованием REGEX_PATTERNS
        try:
            normalized = normalize_with_patterns(parsed, REGEX_PATTERNS)
        except Exception as e:
            logger.error(f"Ошибка при нормализации по REGEX_PATTERNS: {e}")
            normalized = parsed

        return normalized

    except Exception as e:
        logger.error(f"Ошибка при запросе к Qwen3-VL: {e}")
        return None

# ════════════════════════════════════════════════════════════════════════════
# ОБРАБОТКА ОДНОГО И НЕСКОЛЬКИХ PDF
# ════════════════════════════════════════════════════════════════════════════

def process_single_pdf_with_ai(
    pdf_path: Path,
    row_number: int
) -> Tuple[bool, Dict]:
    """
    Обрабатывает один PDF файл с использованием Qwen3-VL.
    """
    pdf_name = pdf_path.name

    try:
        logger.info(f"[{row_number}] Обработка: {pdf_name}")

        data = query_deepseek_ocr(pdf_path)

        if not data:
            logger.warning(f"Модель не вернула данные для {pdf_name}")
            error_row = create_error_row(pdf_name, "AI API не вернул данные", row_number)
            return False, error_row

        row = create_row_from_extracted_data(data, pdf_name, row_number)

        logger.info(f"✓ {pdf_name}")
        return True, row

    except Exception as e:
        logger.error(f"Ошибка при обработке {pdf_name}: {e}")
        error_row = create_error_row(pdf_name, str(e), row_number)
        return False, error_row


def find_pdf_files(search_path: Path) -> List[Path]:
    """Ищет все PDF файлы в папке."""
    if not search_path.exists():
        logger.error(f"Папка не существует: {search_path}")
        return []

    pdf_files = list(search_path.glob("*.pdf")) + list(search_path.glob("*.PDF"))

    if not pdf_files:
        logger.warning(f"Не найдено PDF файлов в {search_path}")
        return []

    return sorted(pdf_files)


def process_all_pdfs_ai(pdf_files: List[Path]) -> Dict:
    """Обрабатывает все PDF файлы с помощью Qwen3-VL AI."""
    logger.info(f"Начало обработки {len(pdf_files)} PDF файлов")

    stats = {
        'total_files': len(pdf_files),
        'successful': 0,
        'failed': 0,
        'rows': [],
        'processing_time': 0,
    }

    start_time = time.time()

    for idx, pdf_file in enumerate(pdf_files, 1):
        success, row = process_single_pdf_with_ai(pdf_file, idx)

        stats['rows'].append(row)

        if success:
            stats['successful'] += 1
        else:
            stats['failed'] += 1

        status_symbol = "✓" if success else "✗"
        print(f"[{idx}/{len(pdf_files)}] {status_symbol} {pdf_file.name}")

    stats['processing_time'] = time.time() - start_time

    return stats

# ════════════════════════════════════════════════════════════════════════════
# РАБОТА С DATAFRAME/EXCEL
# ════════════════════════════════════════════════════════════════════════════

def create_final_dataframe(rows: List[Dict]):
    """Создает финальный DataFrame."""
    df = create_empty_dataframe()

    if rows:
        df = add_rows_batch(df, rows)

    df = fill_numbers_column(df)

    return df


def print_brief_report(stats: Dict, output_file: str = None):
    """Выводит краткий отчет."""
    print(f"\n{'='*70}")
    print(f"✅ ОБРАБОТКА ЗАВЕРШЕНА")
    print(f"{'='*70}")
    print(f"📊 Всего файлов: {stats['total_files']}")
    print(f"✓  Успешно: {stats['successful']}")
    print(f"✗  Ошибок: {stats['failed']}")
    print(f"⏱️  Время: {stats['processing_time']:.2f} сек")

    if output_file:
        print(f"📁 Excel файл: {output_file}")
        print(f"   Размер: {get_file_size(output_file)}")

    print(f"{'='*70}\n")

# ════════════════════════════════════════════════════════════════════════════
# МЕНЮ: ОБРАБОТКА, ПОКАЗ РЕЗУЛЬТАТОВ, ОЧИСТКА
# ════════════════════════════════════════════════════════════════════════════

def process_pdfs_menu():
    """Обрабатывает PDF файлы с выбором папки."""
    print("\n📁 ВЫБОР ПАПКИ")
    print("=" * 70)

    use_default = input("Использовать папку по умолчанию? (да/нет): ").lower().strip()

    if use_default in ['да', 'yes', 'y', '']:
        search_path = INPUT_DIR
        print(f"📁 Используется папка: {search_path}")
    else:
        search_path = get_custom_folder()
        print(f"📁 Используется папка: {search_path}")

    pdf_files = find_pdf_files(search_path)

    if not pdf_files:
        print(f"❌ Не найдено PDF файлов в папке: {search_path}")
        return

    print(f"\n✅ Найдено {len(pdf_files)} PDF файлов:")
    for i, pdf in enumerate(pdf_files, 1):
        print(f"   {i}. {pdf.name}")

    confirm = input("\nПродолжить обработку? (да/нет): ").lower().strip()
    if confirm not in ['да', 'yes', 'y', '']:
        print("❌ Обработка отменена")
        return

    print(f"\n⏳ ОБРАБОТКА В ПРОЦЕССЕ...")
    print("=" * 70 + "\n")

    stats = process_all_pdfs_ai(pdf_files)

    print(f"\n📋 Создание таблицы...")
    df = create_final_dataframe(stats['rows'])

    info = get_dataframe_info(df)
    print(f"✓ Таблица: {info['total_rows']} строк × {info['total_columns']} колонок")

    print(f"📊 Сохранение Excel...")
    output_file = save_dataframe_to_excel(df)

    if output_file:
        print(f"✓ {output_file}")

    print_brief_report(stats, output_file)

    logger.info(f"Обработка завершена: успешно {stats['successful']}/{stats['total_files']}")

def show_last_result():
    """Показывает последний результат."""
    excel_file = OUTPUT_DIR / "output_cadastre_data.xlsx"

    if not excel_file.exists():
        print("\n❌ Результирующий файл не найден")
        return

    import pandas as pd

    df = pd.read_excel(excel_file)

    print(f"\n📊 ПОСЛЕДНИЙ РЕЗУЛЬТАТ")
    print("=" * 70)
    print(f"Файл: {excel_file}")
    print(f"Размер: {get_file_size(str(excel_file))}")
    print(f"Строк: {len(df)}")
    print(f"Колонок: {len(df.columns)}")
    print(f"\n{df.head(5).to_string()}")
    print("=" * 70 + "\n")

def clear_data():
    """Очищает данные."""
    confirm = input("\n⚠️  Вы уверены? Это удалит результирующий Excel файл. (да/нет): ").lower().strip()

    if confirm in ['да', 'yes', 'y']:
        excel_file = OUTPUT_DIR / "output_cadastre_data.xlsx"
        if excel_file.exists():
            excel_file.unlink()
            print("✓ Данные очищены")
        else:
            print("ℹ️  Нечего очищать")
    else:
        print("❌ Отмено")

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    """Главная функция."""

    while True:
        print_menu()
        choice = get_user_choice()

        if choice == 1:
            search_path = INPUT_DIR
            pdf_files = find_pdf_files(search_path)

            if not pdf_files:
                print(f"\n❌ Не найдено PDF файлов в: {search_path}")
                continue

            print(f"\n✅ Найдено {len(pdf_files)} файлов")
            print("⏳ Обработка в процессе...\n")

            stats = process_all_pdfs_ai(pdf_files)

            print(f"\n📋 Создание таблицы...")
            df = create_final_dataframe(stats['rows'])

            info = get_dataframe_info(df)
            print(f"✓ {info['total_rows']} строк")

            print(f"📊 Сохранение Excel...")
            output_file = save_dataframe_to_excel(df)

            print_brief_report(stats, output_file)

        elif choice == 2:
            process_pdfs_menu()

        elif choice == 3:
            show_last_result()

        elif choice == 4:
            clear_data()

        elif choice == 5:
            print("\n👋 До свидания!\n")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Обработка прервана пользователем")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"\n❌ Ошибка: {e}")
        sys.exit(11)
