# -*- coding: utf-8 -*-
"""
Упрощенные утилиты
"""

import logging
from datetime import datetime
from typing import Dict, Any
from simple_database import DatabaseManager

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )

def format_file_size(size_bytes):
    """Форматирование размера файла"""
    if not size_bytes:
        return "Неизвестно"
    
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"

async def is_rate_limited(user_id: int) -> bool:
    """Проверка лимитов"""
    return False  # Упрощенная версия

async def log_user_action(db: DatabaseManager, user_id: str, action: str, data: Dict[str, Any] = None):
    """Логирование действий пользователя"""
    logging.info(f"User {user_id} performed action: {action}")