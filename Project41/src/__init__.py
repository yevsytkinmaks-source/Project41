# -*- coding: utf-8 -*-
"""
Пакет RUУчебник
Модули для работы системы поиска школьных учебников
"""

__version__ = "1.0.0"
__author__ = "RUУчебник Team"

# Импорты для удобства
from .enhanced_bot import EnhancedRUUchebnikBot
from .enhanced_desktop_app import RUUchebnikDesktopApp
from .simple_database import DatabaseManager
from .config import BOT_CONFIG, MESSAGES

__all__ = [
    'EnhancedRUUchebnikBot',
    'RUUchebnikDesktopApp', 
    'DatabaseManager',
    'BOT_CONFIG',
    'MESSAGES'
]