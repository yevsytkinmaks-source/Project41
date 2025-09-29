# -*- coding: utf-8 -*-
"""
Модуль для создания клавиатур и кнопок Telegram бота
Содержит все функции для генерации inline и reply клавиатур

Автор: Разработано для системы RUУчебник
Версия: 1.0.0
"""

from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from config import KEYBOARD_TEXTS


def get_main_keyboard() -> InlineKeyboardMarkup:
    """
    Создание главной inline клавиатуры с основными функциями бота
    
    Returns:
        InlineKeyboardMarkup: Главное меню бота
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text=KEYBOARD_TEXTS['search_textbooks'],
                callback_data='inline_search'
            )
        ],
        [
            InlineKeyboardButton(
                text=KEYBOARD_TEXTS['help'],
                callback_data='inline_help'
            ),
            InlineKeyboardButton(
                text=KEYBOARD_TEXTS['about'],
                callback_data='inline_about'
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_classes_keyboard(classes: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Создание клавиатуры для выбора классов
    
    Args:
        classes: Список классов из базы данных
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками классов
    """
    keyboard = []
    
    # Разбиваем классы по строкам (по 3 кнопки в строке)
    row = []
    for class_data in classes:
        button = InlineKeyboardButton(
            text=class_data['name'],
            callback_data=f"class_{class_data['id']}"
        )
        row.append(button)
        
        # Когда накопилось 3 кнопки, добавляем строку
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    # Добавляем последнюю неполную строку, если есть
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку возврата в главное меню
    keyboard.append([
        InlineKeyboardButton(
            text=KEYBOARD_TEXTS['back_to_menu'],
            callback_data='back_menu'
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_subjects_keyboard(subjects: List[Dict[str, Any]], class_id: str) -> InlineKeyboardMarkup:
    """
    Создание клавиатуры для выбора предметов
    
    Args:
        subjects: Список предметов из базы данных
        class_id: ID выбранного класса
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками предметов
    """
    keyboard = []
    
    # Каждый предмет на отдельной строке для лучшей читаемости
    for subject in subjects:
        button = InlineKeyboardButton(
            text=f"📚 {subject['name']}",
            callback_data=f"subject_{class_id}_{subject['id']}"
        )
        keyboard.append([button])
    
    # Кнопки навигации
    navigation_row = [
        InlineKeyboardButton(
            text=KEYBOARD_TEXTS['back'],
            callback_data='back_classes'
        ),
        InlineKeyboardButton(
            text=KEYBOARD_TEXTS['back_to_menu'],
            callback_data='back_menu'
        )
    ]
    keyboard.append(navigation_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_textbooks_keyboard(textbooks: List[Dict[str, Any]], class_id: str) -> InlineKeyboardMarkup:
    """
    Создание клавиатуры со списком учебников
    
    Args:
        textbooks: Список учебников из базы данных
        class_id: ID класса для кнопки "Назад"
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с учебниками
    """
    keyboard = []
    
    # Каждый учебник на отдельной строке
    for textbook in textbooks:
        # Формируем текст кнопки с автором
        author_name = textbook.get('author_short_name') or textbook.get('author_name', 'Неизвестный автор')
        
        # Ограничиваем длину текста для кнопки
        title = textbook['title']
        if len(title) > 40:
            title = title[:37] + "..."
        
        button_text = f"📖 {title} - {author_name}"
        
        button = InlineKeyboardButton(
            text=button_text,
            callback_data=f"textbook_{textbook['id']}"
        )
        keyboard.append([button])
    
    # Кнопки навигации
    navigation_row = [
        InlineKeyboardButton(
            text=KEYBOARD_TEXTS['back'],
            callback_data=f'back_subjects_{class_id}'
        ),
        InlineKeyboardButton(
            text=KEYBOARD_TEXTS['back_to_menu'],
            callback_data='back_menu'
        )
    ]
    keyboard.append(navigation_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_textbook_details_keyboard(textbook_id: str) -> InlineKeyboardMarkup:
    """
    Создание клавиатуры для страницы с деталями учебника
    
    Args:
        textbook_id: ID учебника
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой скачивания
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text=KEYBOARD_TEXTS['download'],
                callback_data=f"download_{textbook_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text=KEYBOARD_TEXTS['back'],
                callback_data='back_textbooks'
            ),
            InlineKeyboardButton(
                text=KEYBOARD_TEXTS['back_to_menu'],
                callback_data='back_menu'
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """
    Создание простой клавиатуры с кнопкой "Назад в меню"
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text=KEYBOARD_TEXTS['back_to_menu'],
                callback_data='back_menu'
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Создание клавиатуры для администратора
    
    Returns:
        InlineKeyboardMarkup: Админская клавиатура
    """
    keyboard = [
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🔧 Обслуживание", callback_data="admin_maintenance")
        ],
        [
            InlineKeyboardButton(text="📝 Логи", callback_data="admin_logs"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_pagination_keyboard(current_page: int, total_pages: int, 
                           callback_prefix: str, additional_data: str = "") -> InlineKeyboardMarkup:
    """
    Создание клавиатуры с пагинацией
    
    Args:
        current_page: Текущая страница (начинается с 1)
        total_pages: Общее количество страниц
        callback_prefix: Префикс для callback_data
        additional_data: Дополнительные данные для callback
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками пагинации
    """
    keyboard = []
    
    if total_pages > 1:
        pagination_row = []
        
        # Кнопка "Предыдущая страница"
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="◀️ Пред",
                    callback_data=f"{callback_prefix}_page_{current_page - 1}_{additional_data}"
                )
            )
        
        # Информация о текущей странице
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}",
                callback_data="pagination_info"  # Заглушка
            )
        )
        
        # Кнопка "Следующая страница"
        if current_page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="След ▶️",
                    callback_data=f"{callback_prefix}_page_{current_page + 1}_{additional_data}"
                )
            )
        
        keyboard.append(pagination_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_search_filters_keyboard() -> InlineKeyboardMarkup:
    """
    Создание клавиатуры для фильтров поиска
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с фильтрами
    """
    keyboard = [
        [
            InlineKeyboardButton(text="🎓 По классу", callback_data="filter_class"),
            InlineKeyboardButton(text="📚 По предмету", callback_data="filter_subject")
        ],
        [
            InlineKeyboardButton(text="👤 По автору", callback_data="filter_author"),
            InlineKeyboardButton(text="🔍 Поиск по названию", callback_data="filter_title")
        ],
        [
            InlineKeyboardButton(text="⭐ Популярные", callback_data="filter_popular"),
            InlineKeyboardButton(text="🆕 Новые", callback_data="filter_recent")
        ],
        [
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirmation_keyboard(confirm_callback: str, cancel_callback: str = "cancel") -> InlineKeyboardMarkup:
    """
    Создание клавиатуры подтверждения действия
    
    Args:
        confirm_callback: Callback для подтверждения
        cancel_callback: Callback для отмены
        
    Returns:
        InlineKeyboardMarkup: Клавиатура подтверждения
    """
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=confirm_callback),
            InlineKeyboardButton(text="❌ Нет", callback_data=cancel_callback)
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# =============================================================================
# REPLY КЛАВИАТУРЫ (для специальных случаев)
# =============================================================================

def get_contact_keyboard() -> ReplyKeyboardMarkup:
    """
    Создание Reply клавиатуры для запроса контакта
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой поделиться контактом
    """
    keyboard = [
        [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard, 
        resize_keyboard=True, 
        one_time_keyboard=True
    )


def get_location_keyboard() -> ReplyKeyboardMarkup:
    """
    Создание Reply клавиатуры для запроса местоположения
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой поделиться местоположением
    """
    keyboard = [
        [KeyboardButton(text="📍 Поделиться местоположением", request_location=True)]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )


def remove_keyboard() -> dict:
    """
    Убирает Reply клавиатуру
    
    Returns:
        dict: Параметры для удаления клавиатуры
    """
    return {"reply_markup": {"remove_keyboard": True}}
