
# -*- coding: utf-8 -*-
"""
src/__init__.py
---------------
Инициализация пакета src (исходный код).
Импортирует и экспортирует основные модули проекта.
"""

__version__ = "1.0.0"

# Ленивые импорты (import on demand) для оптимизации
# Модули будут загружены только при их использовании

def __getattr__(name):
    """
    Динамическая загрузка модулей для оптимизации памяти.
    Позволяет импортировать модули только при их использовании.
    """
    if name == 'logger_config':
        from . import logger_config
        return logger_config
    elif name == 'settings':
        from . import settings
        return settings
    elif name == 'pdf_parser':
        from . import pdf_parser
        return pdf_parser
    elif name == 'data_extractor':
        from . import data_extractor
        return data_extractor
    elif name == 'table_builder':
        from . import table_builder
        return table_builder
    elif name == 'excel_writer':
        from . import excel_writer
        return excel_writer
    
    raise AttributeError(f"модуль 'src' не имеет атрибута '{name}'")


# Основные модули, доступные для прямого импорта
__all__ = [
    'logger_cfg',
    'settings',
    'pdf_parser',      
    'data_extractor',  
    'table_builder',
    'excel_writer',    
]

# Предзагрузить основные модули (необходимые всегда)
try:
    from . import logger_cfg
    from . import configs
except ImportError as e:
    print(f"⚠️ Ошибка при загрузке основных модулей: {e}")
