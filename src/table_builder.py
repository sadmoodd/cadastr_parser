import pandas as pd

columns = [
    '№ п/п',
    'Адрес, комплекс',
    'Наименование здания',
    'Литера / Строение',
    'Кадастр. номер ЗУ',
    'Кадастр. номер здания',
    '№ помещения',
    'Этаж',
    'Площадь (м²)',
    'Предполагаемое назначение',
    'Статус',
    'Арендатор',
    'Подтверждение из PDF',
    'Примечания и расхождения',
    'Собственник',
    'Обременение (аренда)',
    'PDF-источник'
]


def create_empty_dataframe() -> pd.DataFrame:
    # Создает пустой DataFrame с нужной структурой
    pass

def add_row_to_table(df: pd.DataFrame, data: dict, file_name: str) -> pd.DataFrame:
    # Добавляет одну строку в таблицу (data - словарь извлеченных данных)
    pass

def add_error_row(df: pd.DataFrame, file_name: str, error_msg: str) -> pd.DataFrame:
    # Добавляет пустую строку при ошибке парсинга
    pass

