# -*- coding: utf-8 -*-
"""
Обработчики команд и сообщений для Telegram бота RUУчебник
Содержит всю логику обработки пользовательских взаимодействий

Автор: Разработано для системы RUУчебник  
Версия: 1.0.0
"""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import MESSAGES, KEYBOARD_TEXTS, CLASSES, SUBJECTS, CALLBACK_PATTERNS, FILE_CONFIG
from keyboards import (
    get_main_keyboard, get_classes_keyboard, get_subjects_keyboard, 
    get_textbooks_keyboard, get_textbook_details_keyboard, get_back_keyboard
)
from utils import format_file_size, is_rate_limited, log_user_action
from database import DatabaseManager


# Определение состояний для FSM (Finite State Machine)
class BotStates(StatesGroup):
    """Состояния бота для управления диалогом с пользователем"""
    main_menu = State()          # Главное меню
    selecting_class = State()    # Выбор класса  
    selecting_subject = State()  # Выбор предмета
    viewing_textbooks = State()  # Просмотр учебников
    viewing_textbook = State()   # Просмотр конкретного учебника


logger = logging.getLogger(__name__)


# =============================================================================
# БАЗОВЫЕ КОМАНДЫ БОТА
# =============================================================================

async def cmd_start(message: Message, state: FSMContext, db: DatabaseManager):
    """
    Обработчик команды /start
    Приветствие пользователя и создание записи в БД
    """
    user = message.from_user
    if not user:
        return
    
    try:
        # Проверяем, не заблокирован ли пользователь
        if await db.is_user_blocked(user.id):
            await message.answer(
                "❌ Ваш аккаунт заблокирован. Обратитесь к администратору.",
                reply_markup=None
            )
            return
        
        # Получаем или создаем пользователя в БД
        user_data = await db.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Логируем действие
        await log_user_action(db, str(user.id), "start_command", {
            "username": user.username,
            "first_name": user.first_name
        })
        
        # Отправляем приветственное сообщение
        await message.answer(
            MESSAGES['welcome'],
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        
        # Устанавливаем состояние главного меню
        await state.set_state(BotStates.main_menu)
        
        logger.info(f"👤 Пользователь {user.id} (@{user.username}) запустил бота")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /start для пользователя {user.id}: {e}")
        await message.answer(MESSAGES['error_general'])


async def cmd_help(message: Message, db: DatabaseManager):
    """
    Обработчик команды /help
    Показывает подробную справку по использованию бота
    """
    user = message.from_user
    if not user:
        return
    
    try:
        # Проверяем блокировку
        if await db.is_user_blocked(user.id):
            return
        
        # Обновляем активность пользователя
        await db.update_user_activity(user.id)
        
        # Отправляем справку
        await message.answer(
            MESSAGES['help'],
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        
        logger.info(f"❓ Пользователь {user.id} запросил помощь")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /help для пользователя {user.id}: {e}")
        await message.answer(MESSAGES['error_general'])


async def cmd_about(message: Message, db: DatabaseManager):
    """
    Обработчик команды /about  
    Показывает информацию о проекте и статистику
    """
    user = message.from_user
    if not user:
        return
    
    try:
        # Проверяем блокировку
        if await db.is_user_blocked(user.id):
            return
        
        # Получаем статистику
        stats = await db.get_bot_statistics()
        
        # Форматируем сообщение о проекте
        about_text = MESSAGES['about'].format(
            total_users=stats.get('total_users', 0),
            total_textbooks=stats.get('total_textbooks', 0),
            total_downloads=stats.get('total_downloads', 0)
        )
        
        # Обновляем активность
        await db.update_user_activity(user.id)
        
        await message.answer(
            about_text,
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        
        logger.info(f"ℹ️ Пользователь {user.id} запросил информацию о проекте")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /about для пользователя {user.id}: {e}")
        await message.answer(MESSAGES['error_general'])


async def cmd_search(message: Message, state: FSMContext, db: DatabaseManager):
    """
    Обработчик команды /search
    Начинает процесс поиска учебников
    """
    user = message.from_user
    if not user:
        return
    
    try:
        # Проверяем блокировку и лимиты
        if await db.is_user_blocked(user.id):
            return
        
        if await is_rate_limited(user.id):
            await message.answer(MESSAGES['error_rate_limit'])
            return
        
        # Получаем список классов
        classes = await db.get_classes()
        
        if not classes:
            await message.answer(MESSAGES['error_no_textbooks'])
            return
        
        # Отправляем клавиатуру с классами
        await message.answer(
            MESSAGES['search_select_class'],
            reply_markup=get_classes_keyboard(classes)
        )
        
        # Устанавливаем состояние выбора класса
        await state.set_state(BotStates.selecting_class)
        
        # Обновляем активность
        await db.update_user_activity(user.id)
        
        logger.info(f"🔍 Пользователь {user.id} начал поиск учебников")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /search для пользователя {user.id}: {e}")
        await message.answer(MESSAGES['error_general'])


# =============================================================================
# ОБРАБОТЧИКИ CALLBACK ЗАПРОСОВ  
# =============================================================================

async def process_class_selection(callback: CallbackQuery, state: FSMContext, db: DatabaseManager):
    """
    Обработка выбора класса пользователем
    """
    user = callback.from_user
    if not user:
        return
    
    try:
        # Извлекаем ID класса из callback_data
        class_id = callback.data.replace('class_', '')
        
        # Получаем предметы для выбранного класса
        subjects = await db.get_subjects_by_class(class_id)
        
        if not subjects:
            await callback.message.edit_text(
                MESSAGES['error_no_textbooks'],
                reply_markup=get_back_keyboard()
            )
            return
        
        # Получаем информацию о классе
        classes = await db.get_classes()
        class_name = next((c['name'] for c in classes if c['id'] == class_id), f"Класс {class_id}")
        
        # Отправляем клавиатуру с предметами
        await callback.message.edit_text(
            MESSAGES['search_select_subject'].format(class_name=class_name),
            reply_markup=get_subjects_keyboard(subjects, class_id)
        )
        
        # Сохраняем выбранный класс в состоянии
        await state.update_data(selected_class_id=class_id, selected_class_name=class_name)
        await state.set_state(BotStates.selecting_subject)
        
        # Отвечаем на callback
        await callback.answer()
        
        # Обновляем активность
        await db.update_user_activity(user.id)
        
        logger.info(f"🎓 Пользователь {user.id} выбрал класс: {class_name}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при выборе класса пользователем {user.id}: {e}")
        await callback.answer(MESSAGES['error_general'], show_alert=True)


async def process_subject_selection(callback: CallbackQuery, state: FSMContext, db: DatabaseManager):
    """
    Обработка выбора предмета пользователем
    """
    user = callback.from_user
    if not user:
        return
    
    try:
        # Извлекаем данные из callback_data: subject_class_id_subject_id
        parts = callback.data.replace('subject_', '').split('_', 1)
        class_id = parts[0]
        subject_id = parts[1]
        
        # Получаем данные из состояния
        state_data = await state.get_data()
        class_name = state_data.get('selected_class_name', f'Класс {class_id}')
        
        # Получаем учебники для выбранного класса и предмета
        textbooks = await db.get_textbooks(class_id, subject_id)
        
        if not textbooks:
            await callback.message.edit_text(
                MESSAGES['error_no_textbooks'],
                reply_markup=get_back_keyboard()
            )
            return
        
        # Получаем название предмета
        subject_name = textbooks[0]['subject_name'] if textbooks else 'Неизвестный предмет'
        
        # Отправляем список учебников
        await callback.message.edit_text(
            MESSAGES['search_select_textbook'].format(
                subject_name=subject_name,
                class_name=class_name
            ),
            reply_markup=get_textbooks_keyboard(textbooks, class_id),
            parse_mode='HTML'
        )
        
        # Обновляем состояние
        await state.update_data(
            selected_subject_id=subject_id, 
            selected_subject_name=subject_name,
            textbooks=textbooks
        )
        await state.set_state(BotStates.viewing_textbooks)
        
        await callback.answer()
        
        # Обновляем активность
        await db.update_user_activity(user.id)
        
        logger.info(f"📚 Пользователь {user.id} выбрал предмет: {subject_name} для {class_name}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при выборе предмета пользователем {user.id}: {e}")
        await callback.answer(MESSAGES['error_general'], show_alert=True)


async def process_textbook_selection(callback: CallbackQuery, state: FSMContext, db: DatabaseManager):
    """
    Обработка выбора конкретного учебника
    """
    user = callback.from_user  
    if not user:
        return
    
    try:
        # Извлекаем ID учебника
        textbook_id = callback.data.replace('textbook_', '')
        
        # Получаем подробную информацию об учебнике
        textbook = await db.get_textbook(textbook_id)
        
        if not textbook:
            await callback.answer(MESSAGES['error_file_not_found'], show_alert=True)
            return
        
        # Форматируем размер файла
        file_size_str = format_file_size(textbook.get('file_size', 0))
        
        # Формируем информационное сообщение
        info_text = MESSAGES['search_textbook_info'].format(
            title=textbook['title'],
            author=textbook.get('author_short_name') or textbook.get('author_name', 'Неизвестный автор'),
            class_name=textbook.get('class_name', 'Неизвестный класс'),
            subject_name=textbook.get('subject_name', 'Неизвестный предмет'),
            file_size=file_size_str,
            downloads=textbook.get('download_count', 0)
        )
        
        # Отправляем информацию с кнопкой скачивания
        await callback.message.edit_text(
            info_text,
            reply_markup=get_textbook_details_keyboard(textbook_id),
            parse_mode='HTML'
        )
        
        # Сохраняем выбранный учебник в состоянии
        await state.update_data(selected_textbook=textbook)
        await state.set_state(BotStates.viewing_textbook)
        
        await callback.answer()
        
        # Обновляем активность
        await db.update_user_activity(user.id)
        
        logger.info(f"📖 Пользователь {user.id} просматривает учебник: {textbook['title']}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при просмотре учебника пользователем {user.id}: {e}")
        await callback.answer(MESSAGES['error_general'], show_alert=True)


async def process_textbook_download(callback: CallbackQuery, state: FSMContext, db: DatabaseManager):
    """
    Обработка скачивания учебника
    """
    user = callback.from_user
    if not user:
        return
    
    try:
        # Проверяем лимиты
        if await is_rate_limited(user.id):
            await callback.answer(MESSAGES['error_rate_limit'], show_alert=True)
            return
        
        # Извлекаем ID учебника
        textbook_id = callback.data.replace('download_', '')
        
        # Получаем информацию об учебнике
        textbook = await db.get_textbook(textbook_id)
        
        if not textbook or not os.path.exists(textbook['file_path']):
            await callback.answer(MESSAGES['error_file_not_found'], show_alert=True)
            return
        
        # Уведомляем о начале скачивания
        await callback.answer(MESSAGES['success_download_started'])
        
        # Отправляем "печатающий" статус
        await callback.message.answer_chat_action('upload_document')
        
        try:
            # Отправляем файл
            file_to_send = FSInputFile(textbook['file_path'])
            
            await callback.message.answer_document(
                document=file_to_send,
                caption=f"📖 <b>{textbook['title']}</b>\n"
                       f"👤 <b>Автор:</b> {textbook.get('author_name', 'Неизвестный автор')}\n"
                       f"🎓 <b>Класс:</b> {textbook.get('class_name', '')}\n"
                       f"📚 <b>Предмет:</b> {textbook.get('subject_name', '')}",
                parse_mode='HTML'
            )
            
            # Увеличиваем счетчики
            await db.increment_textbook_downloads(textbook_id)
            await db.increment_user_downloads(user.id)
            
            # Логируем скачивание
            user_data = await db.get_or_create_user(user.id)
            await db.log_download(user_data['id'], textbook_id)
            
            # Логируем действие
            await log_user_action(db, str(user.id), "textbook_downloaded", {
                "textbook_id": textbook_id,
                "textbook_title": textbook['title'],
                "author": textbook.get('author_name'),
                "class": textbook.get('class_name'),
                "subject": textbook.get('subject_name')
            })
            
            logger.info(f"📥 Пользователь {user.id} скачал учебник: {textbook['title']}")
            
        except Exception as file_error:
            logger.error(f"❌ Ошибка при отправке файла пользователю {user.id}: {file_error}")
            await callback.message.answer(MESSAGES['error_download_failed'])
    
    except Exception as e:
        logger.error(f"❌ Ошибка при скачивании учебника пользователем {user.id}: {e}")
        await callback.answer(MESSAGES['error_general'], show_alert=True)


# =============================================================================
# НАВИГАЦИОННЫЕ ОБРАБОТЧИКИ
# =============================================================================

async def process_back_to_classes(callback: CallbackQuery, state: FSMContext, db: DatabaseManager):
    """Возврат к выбору классов"""
    try:
        classes = await db.get_classes()
        
        await callback.message.edit_text(
            MESSAGES['search_select_class'],
            reply_markup=get_classes_keyboard(classes)
        )
        
        await state.set_state(BotStates.selecting_class)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при возврате к классам: {e}")
        await callback.answer(MESSAGES['error_general'], show_alert=True)


async def process_back_to_subjects(callback: CallbackQuery, state: FSMContext, db: DatabaseManager):
    """Возврат к выбору предметов"""
    try:
        # Получаем данные из состояния
        state_data = await state.get_data()
        class_id = state_data.get('selected_class_id')
        class_name = state_data.get('selected_class_name')
        
        if not class_id:
            # Если данных нет, возвращаемся к классам
            await process_back_to_classes(callback, state, db)
            return
        
        subjects = await db.get_subjects_by_class(class_id)
        
        await callback.message.edit_text(
            MESSAGES['search_select_subject'].format(class_name=class_name),
            reply_markup=get_subjects_keyboard(subjects, class_id)
        )
        
        await state.set_state(BotStates.selecting_subject)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при возврате к предметам: {e}")
        await callback.answer(MESSAGES['error_general'], show_alert=True)


async def process_back_to_menu(callback: CallbackQuery, state: FSMContext, db: DatabaseManager):
    """Возврат в главное меню"""
    try:
        await callback.message.edit_text(
            MESSAGES['welcome'],
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        
        await state.set_state(BotStates.main_menu)
        await state.clear()  # Очищаем данные состояния
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при возврате в меню: {e}")
        await callback.answer(MESSAGES['error_general'], show_alert=True)


# =============================================================================
# ОБРАБОТКА ИНЛАЙН КНОПОК ИЗ ОСНОВНОГО МЕНЮ
# =============================================================================

async def process_inline_search(callback: CallbackQuery, state: FSMContext, db: DatabaseManager):
    """Обработка кнопки 'Поиск учебников' из главного меню"""
    # Перенаправляем на обработчик команды search
    message_obj = callback.message
    message_obj.from_user = callback.from_user  # Подменяем пользователя
    await cmd_search(message_obj, state, db)
    await callback.answer()


async def process_inline_help(callback: CallbackQuery, db: DatabaseManager):
    """Обработка кнопки 'Помощь' из главного меню"""
    message_obj = callback.message
    message_obj.from_user = callback.from_user
    await cmd_help(message_obj, db)
    await callback.answer()


async def process_inline_about(callback: CallbackQuery, db: DatabaseManager):
    """Обработка кнопки 'О проекте' из главного меню"""  
    message_obj = callback.message
    message_obj.from_user = callback.from_user
    await cmd_about(message_obj, db)
    await callback.answer()


# =============================================================================
# РЕГИСТРАЦИЯ ВСЕХ ОБРАБОТЧИКОВ
# =============================================================================

def register_all_handlers(dp: Dispatcher):
    """
    Регистрация всех обработчиков команд и callback'ов
    
    Args:
        dp: Экземпляр Dispatcher для регистрации обработчиков
    """
    
    # Команды бота
    dp.message.register(cmd_start, Command(commands=['start']))
    dp.message.register(cmd_help, Command(commands=['help']))
    dp.message.register(cmd_about, Command(commands=['about']))
    dp.message.register(cmd_search, Command(commands=['search']))
    
    # Callback обработчики для выбора классов, предметов и учебников
    dp.callback_query.register(process_class_selection, F.data.startswith('class_'))
    dp.callback_query.register(process_subject_selection, F.data.startswith('subject_'))
    dp.callback_query.register(process_textbook_selection, F.data.startswith('textbook_'))
    dp.callback_query.register(process_textbook_download, F.data.startswith('download_'))
    
    # Навигационные callback'ы
    dp.callback_query.register(process_back_to_classes, F.data == 'back_classes')
    dp.callback_query.register(process_back_to_subjects, F.data.startswith('back_subjects_'))
    dp.callback_query.register(process_back_to_menu, F.data == 'back_menu')
    
    # Инлайн кнопки из главного меню
    dp.callback_query.register(process_inline_search, F.data == 'inline_search')
    dp.callback_query.register(process_inline_help, F.data == 'inline_help')
    dp.callback_query.register(process_inline_about, F.data == 'inline_about')
    
    logger.info("✅ Все обработчики команд и callback'ов зарегистрированы")
