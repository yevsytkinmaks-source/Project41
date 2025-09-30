# -*- coding: utf-8 -*-
"""
Упрощенные обработчики для демонстрации
"""

import logging
from aiogram import Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from simple_database import DatabaseManager
from keyboards import get_main_keyboard

logger = logging.getLogger(__name__)

async def cmd_start(message: Message, db: DatabaseManager):
    """Обработчик команды /start"""
    user = message.from_user
    if not user:
        return
    
    try:
        # Создаем пользователя в БД
        await db.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        await message.answer(
            "🎓 <b>Добро пожаловать в RUУчебник!</b>\n\n"
            "Ваш персональный помощник для поиска школьных учебников.\n\n"
            "Используйте /help для получения справки.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
❓ <b>Справка по использованию RUУчебник</b>

🔍 <b>Функции:</b>
• /start - Главное меню
• /help - Эта справка
• /about - О проекте

📚 Бот находится в разработке.
    """
    await message.answer(help_text, parse_mode="HTML")

async def cmd_about(message: Message):
    """Обработчик команды /about"""
    about_text = """
ℹ️ <b>О проекте RUУчебник</b>

Система для поиска и скачивания школьных учебников.

🏗️ Статус: В разработке
    """
    await message.answer(about_text, parse_mode="HTML")

def register_all_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_about, Command("about"))