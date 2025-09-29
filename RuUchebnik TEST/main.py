#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный файл Telegram бота RUУчебник
Обеспечивает поиск и скачивание школьных учебников

Автор: Разработано для системы RUУчебник
Версия: 1.0.0
Дата: 2023
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем корневую папку в путь для импорта модулей
sys.path.append(str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_CONFIG, MESSAGES
from database import DatabaseManager
from handlers import register_all_handlers
from utils import setup_logging


async def main():
    """Основная функция запуска бота"""
    
    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Запуск Telegram бота RUУчебник...")
    
    # Проверка наличия токена бота
    bot_token = BOT_CONFIG.get('token')
    if not bot_token:
        logger.error("❌ Токен бота не найден! Проверьте переменную окружения BOT_TOKEN")
        sys.exit(1)
    
    try:
        # Инициализация базы данных
        logger.info("📊 Инициализация подключения к базе данных...")
        db_manager = DatabaseManager()
        await db_manager.initialize()
        logger.info("✅ Подключение к базе данных установлено")
        
        # Создание экземпляра бота с настройками по умолчанию
        bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Создание диспетчера с хранилищем в памяти
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Передача экземпляра менеджера БД в диспетчер для доступа в обработчиках
        dp["db"] = db_manager
        
        # Регистрация всех обработчиков команд и сообщений
        register_all_handlers(dp)
        
        # Проверка подключения к Telegram API
        logger.info("🔗 Проверка подключения к Telegram API...")
        bot_info = await bot.get_me()
        logger.info(f"✅ Бот успешно подключен: @{bot_info.username} ({bot_info.first_name})")
        
        # Установка команд бота в меню
        from aiogram.types import BotCommand
        await bot.set_my_commands([
            BotCommand(command="start", description="🏠 Начать работу с ботом"),
            BotCommand(command="search", description="🔍 Поиск учебников"),
            BotCommand(command="help", description="❓ Помощь и инструкции"),
            BotCommand(command="about", description="ℹ️ О проекте RUУчебник")
        ])
        
        logger.info("📋 Команды бота установлены в меню")
        
        # Отправка уведомления администратору о запуске
        admin_id = BOT_CONFIG.get('admin_id')
        if admin_id:
            try:
                await bot.send_message(
                    admin_id, 
                    "🟢 <b>Бот RUУчебник запущен!</b>\n\n"
                    f"🤖 <b>Имя:</b> {bot_info.first_name}\n"
                    f"👤 <b>Username:</b> @{bot_info.username}\n"
                    f"🆔 <b>ID:</b> {bot_info.id}\n\n"
                    "Система готова к работе! ✅"
                )
                logger.info("📨 Уведомление администратору отправлено")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось отправить уведомление администратору: {e}")
        
        # Запуск polling (получение обновлений от Telegram)
        logger.info("🔄 Запуск polling для получения обновлений...")
        logger.info("🎯 Бот готов к работе! Нажмите Ctrl+C для остановки")
        
        await dp.start_polling(bot, drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("⏹️ Получен сигнал остановки от пользователя")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка при запуске бота: {e}")
        sys.exit(1)
    finally:
        # Закрытие подключения к базе данных
        if 'db_manager' in locals():
            await db_manager.close()
            logger.info("📊 Подключение к базе данных закрыто")
        
        # Закрытие сессии бота
        if 'bot' in locals():
            await bot.session.close()
            logger.info("🤖 Сессия бота закрыта")
        
        logger.info("👋 Бот RUУчебник остановлен")


if __name__ == "__main__":
    try:
        # Запуск основной функции в асинхронном режиме
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"💥 Ошибка запуска: {e}")
        sys.exit(1)
