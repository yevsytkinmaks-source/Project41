# -*- coding: utf-8 -*-
"""
Вспомогательные утилиты для Telegram бота RUУчебник
Содержит функции для форматирования, лимитов, логирования и других общих задач

Автор: Разработано для системы RUУчебник
Версия: 1.0.0
"""

import logging
import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from config import BOT_CONFIG, LOGGING_CONFIG
from database import DatabaseManager


# Глобальное хранилище для rate limiting
_rate_limit_storage: Dict[int, List[float]] = {}

# Настройка логирования
def setup_logging():
    """
    Настройка системы логирования для бота
    Устанавливает формат, уровень и кодировку логов
    """
    logging.basicConfig(
        level=getattr(logging, LOGGING_CONFIG['level']),
        format=LOGGING_CONFIG['format'],
        datefmt=LOGGING_CONFIG['date_format'],
        encoding=LOGGING_CONFIG.get('encoding', 'utf-8'),
        handlers=[
            logging.StreamHandler(),  # Вывод в консоль
            logging.FileHandler('bot.log', encoding='utf-8')  # Запись в файл
        ]
    )
    
    # Настройка уровня логирования для HTTP библиотек
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('aiogram.event').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("🔧 Система логирования настроена")


def format_file_size(size_bytes: Optional[Union[int, float]]) -> str:
    """
    Форматирование размера файла в читаемый вид
    
    Args:
        size_bytes: Размер файла в байтах
        
    Returns:
        str: Отформатированный размер (например, "15.2 МБ")
    """
    if not size_bytes or size_bytes <= 0:
        return "Неизвестно"
    
    # Константы для перевода размеров
    size_names = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
    
    # Определяем подходящую единицу измерения
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024.0 and unit_index < len(size_names) - 1:
        size /= 1024.0
        unit_index += 1
    
    # Форматируем с нужным количеством знаков после запятой
    if unit_index == 0:  # Байты - без дробной части
        return f"{int(size)} {size_names[unit_index]}"
    else:
        return f"{size:.1f} {size_names[unit_index]}"


async def is_rate_limited(user_id: int, max_requests: Optional[int] = None, 
                         window_seconds: Optional[int] = None) -> bool:
    """
    Проверка лимита частоты запросов для пользователя
    
    Args:
        user_id: ID пользователя Telegram
        max_requests: Максимальное количество запросов (из конфига, если не указано)
        window_seconds: Окно времени в секундах (из конфига, если не указано)
        
    Returns:
        bool: True если превышен лимит, False если можно продолжать
    """
    global _rate_limit_storage
    
    # Используем значения из конфигурации по умолчанию
    if max_requests is None:
        max_requests = BOT_CONFIG['rate_limit_requests']
    if window_seconds is None:
        window_seconds = BOT_CONFIG['rate_limit_window']
    
    current_time = time.time()
    
    # Получаем историю запросов пользователя
    user_requests = _rate_limit_storage.get(user_id, [])
    
    # Убираем старые запросы за пределами временного окна
    cutoff_time = current_time - window_seconds
    user_requests = [req_time for req_time in user_requests if req_time > cutoff_time]
    
    # Проверяем превышение лимита
    if len(user_requests) >= max_requests:
        return True
    
    # Добавляем текущий запрос
    user_requests.append(current_time)
    _rate_limit_storage[user_id] = user_requests
    
    return False


def get_rate_limit_reset_time(user_id: int) -> Optional[datetime]:
    """
    Получение времени сброса лимита для пользователя
    
    Args:
        user_id: ID пользователя Telegram
        
    Returns:
        Optional[datetime]: Время сброса лимита или None если лимит не превышен
    """
    global _rate_limit_storage
    
    user_requests = _rate_limit_storage.get(user_id, [])
    if not user_requests:
        return None
    
    # Время сброса = время первого запроса + окно лимита
    oldest_request = min(user_requests)
    reset_time = datetime.fromtimestamp(oldest_request + BOT_CONFIG['rate_limit_window'])
    
    return reset_time if reset_time > datetime.now() else None


async def log_user_action(db: DatabaseManager, user_id: str, action: str, 
                         details: Optional[Dict[str, Any]] = None):
    """
    Логирование действия пользователя в системе
    
    Args:
        db: Экземпляр менеджера базы данных
        user_id: ID пользователя
        action: Описание действия
        details: Дополнительные детали действия
    """
    try:
        await db.log_system_event(
            event_type="info",
            action=action,
            details=details or {},
            user_id=user_id
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Ошибка логирования действия пользователя {user_id}: {e}")


def format_datetime(dt: datetime, include_time: bool = True, 
                   include_seconds: bool = False) -> str:
    """
    Форматирование даты и времени для отображения пользователю
    
    Args:
        dt: Объект datetime для форматирования
        include_time: Включать ли время в результат
        include_seconds: Включать ли секунды (работает только если include_time=True)
        
    Returns:
        str: Отформатированная дата/время
    """
    if not include_time:
        return dt.strftime("%d.%m.%Y")
    
    time_format = "%H:%M:%S" if include_seconds else "%H:%M"
    return dt.strftime(f"%d.%m.%Y {time_format}")


def format_duration(seconds: int) -> str:
    """
    Форматирование продолжительности в читаемый вид
    
    Args:
        seconds: Продолжительность в секундах
        
    Returns:
        str: Отформатированная продолжительность
    """
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} мин"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}ч {minutes}м"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}д {hours}ч"


def create_file_hash(file_path: Union[str, Path], algorithm: str = 'md5') -> str:
    """
    Создание хеша файла для проверки целостности
    
    Args:
        file_path: Путь к файлу
        algorithm: Алгоритм хеширования ('md5', 'sha1', 'sha256')
        
    Returns:
        str: Хеш файла в шестнадцатеричном формате
        
    Raises:
        FileNotFoundError: Если файл не найден
        ValueError: Если алгоритм не поддерживается
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    
    # Выбираем алгоритм хеширования
    if algorithm == 'md5':
        hash_obj = hashlib.md5()
    elif algorithm == 'sha1':
        hash_obj = hashlib.sha1()
    elif algorithm == 'sha256':
        hash_obj = hashlib.sha256()
    else:
        raise ValueError(f"Неподдерживаемый алгоритм: {algorithm}")
    
    # Читаем файл по частям для экономии памяти
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def validate_file_type(file_path: Union[str, Path], 
                      allowed_extensions: Optional[List[str]] = None) -> bool:
    """
    Проверка типа файла по расширению
    
    Args:
        file_path: Путь к файлу
        allowed_extensions: Список разрешенных расширений (из конфига, если не указано)
        
    Returns:
        bool: True если тип файла разрешен
    """
    if allowed_extensions is None:
        from config import FILE_CONFIG
        allowed_extensions = FILE_CONFIG['allowed_extensions']
    
    file_path = Path(file_path)
    file_extension = file_path.suffix.lower()
    
    return file_extension in [ext.lower() for ext in allowed_extensions]


def sanitize_filename(filename: str) -> str:
    """
    Очистка имени файла от недопустимых символов
    
    Args:
        filename: Исходное имя файла
        
    Returns:
        str: Очищенное имя файла
    """
    # Символы, которые нужно удалить или заменить
    invalid_chars = '<>:"/\\|?*'
    
    # Заменяем недопустимые символы на подчеркивание
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Убираем множественные подчеркивания и пробелы
    filename = '_'.join(filename.split())
    
    # Ограничиваем длину имени файла
    if len(filename) > 200:
        name_part, ext_part = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_length = 200 - len(ext_part) - 1 if ext_part else 200
        filename = f"{name_part[:max_name_length]}.{ext_part}" if ext_part else name_part[:200]
    
    return filename


async def cleanup_rate_limit_storage(max_age_hours: int = 24):
    """
    Очистка устаревших записей из хранилища лимитов
    
    Args:
        max_age_hours: Максимальный возраст записей в часах
    """
    global _rate_limit_storage
    
    cutoff_time = time.time() - (max_age_hours * 3600)
    
    users_to_remove = []
    for user_id, requests in _rate_limit_storage.items():
        # Фильтруем старые запросы
        recent_requests = [req_time for req_time in requests if req_time > cutoff_time]
        
        if recent_requests:
            _rate_limit_storage[user_id] = recent_requests
        else:
            users_to_remove.append(user_id)
    
    # Удаляем пользователей без недавних запросов
    for user_id in users_to_remove:
        del _rate_limit_storage[user_id]
    
    logger = logging.getLogger(__name__)
    if users_to_remove:
        logger.info(f"🧹 Очищены данные лимитов для {len(users_to_remove)} пользователей")


def format_number(number: int, use_thousands_separator: bool = True) -> str:
    """
    Форматирование числа для отображения
    
    Args:
        number: Число для форматирования
        use_thousands_separator: Использовать ли разделитель тысяч
        
    Returns:
        str: Отформатированное число
    """
    if use_thousands_separator:
        return f"{number:,}".replace(",", " ")
    else:
        return str(number)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Обрезка текста до максимальной длины с добавлением суффикса
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина результата
        suffix: Суффикс для обрезанного текста
        
    Returns:
        str: Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    
    # Учитываем длину суффикса
    truncate_at = max_length - len(suffix)
    if truncate_at <= 0:
        return suffix[:max_length]
    
    return text[:truncate_at] + suffix


def get_user_display_name(first_name: Optional[str], last_name: Optional[str], 
                         username: Optional[str]) -> str:
    """
    Получение отображаемого имени пользователя
    
    Args:
        first_name: Имя пользователя
        last_name: Фамилия пользователя
        username: Имя пользователя в Telegram
        
    Returns:
        str: Отображаемое имя пользователя
    """
    if first_name and last_name:
        return f"{first_name} {last_name}"
    elif first_name:
        return first_name
    elif username:
        return f"@{username}"
    else:
        return "Без имени"


async def safe_delete_file(file_path: Union[str, Path]) -> bool:
    """
    Безопасное удаление файла с обработкой ошибок
    
    Args:
        file_path: Путь к файлу для удаления
        
    Returns:
        bool: True если файл успешно удален или не существует
    """
    try:
        file_path = Path(file_path)
        if file_path.exists():
            file_path.unlink()
            return True
        return True  # Файл не существует - считаем это успехом
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Ошибка удаления файла {file_path}: {e}")
        return False


def create_pagination_text(current_page: int, total_pages: int, 
                          items_per_page: int, total_items: int) -> str:
    """
    Создание текста пагинации
    
    Args:
        current_page: Текущая страница (начинается с 1)
        total_pages: Общее количество страниц
        items_per_page: Элементов на странице
        total_items: Общее количество элементов
        
    Returns:
        str: Текст пагинации
    """
    start_item = (current_page - 1) * items_per_page + 1
    end_item = min(current_page * items_per_page, total_items)
    
    return f"Показано {start_item}-{end_item} из {total_items} | Страница {current_page} из {total_pages}"


# Периодическая задача для очистки хранилища лимитов
async def start_periodic_cleanup():
    """
    Запуск периодической очистки данных
    """
    logger = logging.getLogger(__name__)
    logger.info("🔄 Запущена периодическая очистка данных")
    
    while True:
        try:
            await cleanup_rate_limit_storage()
            # Очистка каждые 6 часов
            await asyncio.sleep(6 * 3600)
        except Exception as e:
            logger.error(f"❌ Ошибка в периодической очистке: {e}")
            # При ошибке ждем меньше и пробуем снова
            await asyncio.sleep(1800)  # 30 минут


def escape_markdown(text: str) -> str:
    """
    Экранирование символов для Markdown разметки в Telegram
    
    Args:
        text: Исходный текст
        
    Returns:
        str: Экранированный текст
    """
    escape_chars = '_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


def escape_html(text: str) -> str:
    """
    Экранирование HTML символов для HTML разметки в Telegram
    
    Args:
        text: Исходный текст
        
    Returns:
        str: Экранированный текст
    """
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))
