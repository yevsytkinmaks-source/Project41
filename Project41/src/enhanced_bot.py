#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенный Telegram бот RUУчебник с потоком согласия с правилами
Включает меню Решатор/Учебники, управление изображениями и админ-панель
"""

import asyncio
import logging
import os
import sys
import json
from pathlib import Path
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_CONFIG, MESSAGES
from simple_database import DatabaseManager
from simple_utils import setup_logging


class BotStates(StatesGroup):
    """Состояния бота"""
    waiting_for_rules_agreement = State()
    main_menu = State()
    solver_menu = State()
    textbooks_menu = State()
    selecting_class = State()
    selecting_subject = State()
    viewing_textbooks = State()
    help_mode = State()


class EnhancedRUUchebnikBot:
    def __init__(self):
        self.db_manager = None
        self.bot = None
        self.dp = None
        self.images_dir = "images"
        self.ensure_images_directory()
        
    def ensure_images_directory(self):
        """Создание директории для изображений если её нет"""
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
        
        for subdir in ["rules", "solver", "textbooks", "help"]:
            path = os.path.join(self.images_dir, subdir)
            if not os.path.exists(path):
                os.makedirs(path)
    
    def get_image_path(self, image_type: str) -> str:
        """Получение пути к изображению определенного типа"""
        image_dir = os.path.join(self.images_dir, image_type)
        if os.path.exists(image_dir):
            for file in os.listdir(image_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    return os.path.join(image_dir, file)
        return None
    
    def get_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Создание главного меню с изображениями"""
        keyboard = [
            [
                InlineKeyboardButton(text="🧮 Решатор", callback_data="menu_solver"),
                InlineKeyboardButton(text="📚 Учебники", callback_data="menu_textbooks")
            ],
            [
                InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help"),
                InlineKeyboardButton(text="ℹ️ О проекте", callback_data="menu_about")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def get_rules_keyboard(self) -> InlineKeyboardMarkup:
        """Клавиатура для принятия правил"""
        keyboard = [
            [InlineKeyboardButton(text="✅ Да, я согласен с правилами", callback_data="agree_rules")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def get_classes_keyboard(self) -> InlineKeyboardMarkup:
        """Клавиатура выбора класса"""
        keyboard = []
        
        # Создаем кнопки для классов по 3 в ряду
        row = []
        for i in range(1, 12):
            row.append(InlineKeyboardButton(text=f"{i} класс", callback_data=f"class_{i}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        # Добавляем оставшиеся классы
        if row:
            keyboard.append(row)
        
        # Кнопка назад
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def get_subjects_keyboard(self, class_num: str) -> InlineKeyboardMarkup:
        """Клавиатура выбора предмета"""
        subjects = [
            ("📐 Математика", "math"),
            ("📝 Русский язык", "russian"),
            ("📖 Литература", "literature"),
            ("⚗️ Физика", "physics"),
            ("🧪 Химия", "chemistry"),
            ("🌱 Биология", "biology"),
            ("🌍 География", "geography"),
            ("🏛️ История", "history"),
            ("🇬🇧 Английский", "english")
        ]
        
        keyboard = []
        for name, code in subjects:
            keyboard.append([InlineKeyboardButton(text=name, callback_data=f"subject_{class_num}_{code}")])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад к классам", callback_data="back_classes")])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def get_author_help_keyboard(self) -> InlineKeyboardMarkup:
        """Клавиатура помощи по выбору автора"""
        keyboard = [
            [InlineKeyboardButton(text="❓ Где посмотреть автора?", callback_data="help_author")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_textbooks")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    async def start_command(self, message: Message, state: FSMContext):
        """Обработчик команды /start"""
        user = message.from_user
        if not user:
            return
        
        logger = logging.getLogger(__name__)
        
        try:
            # Проверяем, заблокирован ли пользователь
            if await self.db_manager.is_user_blocked(user.id):
                await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь к администратору.")
                return
            
            # Получаем или создаем пользователя
            user_data = await self.db_manager.get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Если пользователь новый, показываем правила
            if user_data.get('is_new', False):
                await self.show_rules(message, state)
            else:
                await self.show_main_menu(message, state)
                
        except Exception as e:
            logger.error(f"Ошибка в /start: {e}")
            await message.answer("Произошла ошибка. Попробуйте позже.")
    
    async def show_rules(self, message: Message, state: FSMContext):
        """Показ правил с изображением"""
        rules_text = """
🔒 <b>Правила использования RUУчебник</b>

1. 📚 Используйте бота только для образовательных целей
2. 🚫 Запрещено распространение материалов без разрешения авторов
3. 👥 Будьте вежливы с другими пользователями
4. 📝 Соблюдайте авторские права
5. 🔐 Не передавайте свой аккаунт третьим лицам

<i>Продолжая использование бота, вы соглашаетесь с данными правилами.</i>
        """
        
        # Получаем изображение правил
        rules_image_path = self.get_image_path("rules")
        
        if rules_image_path:
            # Отправляем изображение с правилами
            photo = FSInputFile(rules_image_path)
            await message.answer_photo(
                photo=photo,
                caption=rules_text,
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_rules_keyboard()
            )
        else:
            # Отправляем только текст, если нет изображения
            await message.answer(
                rules_text,
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_rules_keyboard()
            )
        
        await state.set_state(BotStates.waiting_for_rules_agreement)
    
    async def handle_rules_agreement(self, callback: CallbackQuery, state: FSMContext):
        """Обработка согласия с правилами"""
        if callback.data == "agree_rules":
            # Удаляем сообщение с правилами
            await callback.message.delete()
            
            # Показываем главное меню
            await self.show_main_menu_from_callback(callback, state)
            await callback.answer("Добро пожаловать в RUУчебник! 🎓")
    
    async def show_main_menu(self, message: Message, state: FSMContext):
        """Показ главного меню"""
        menu_text = """
🎓 <b>Главное меню RUУчебник</b>

Выберите нужную функцию:

🧮 <b>Решатор</b> - Решение задач и примеров
📚 <b>Учебники</b> - Поиск и скачивание учебников
❓ <b>Помощь</b> - Справка по использованию
ℹ️ <b>О проекте</b> - Информация о RUУчебник
        """
        
        await message.answer(
            menu_text,
            parse_mode=ParseMode.HTML,
            reply_markup=self.get_main_menu_keyboard()
        )
        
        await state.set_state(BotStates.main_menu)
    
    async def show_main_menu_from_callback(self, callback: CallbackQuery, state: FSMContext):
        """Показ главного меню из callback"""
        menu_text = """
🎓 <b>Главное меню RUУчебник</b>

Выберите нужную функцию:

🧮 <b>Решатор</b> - Решение задач и примеров
📚 <b>Учебники</b> - Поиск и скачивание учебников
❓ <b>Помощь</b> - Справка по использованию
ℹ️ <b>О проекте</b> - Информация о RUУчебник
        """
        
        await callback.message.edit_text(
            menu_text,
            parse_mode=ParseMode.HTML,
            reply_markup=self.get_main_menu_keyboard()
        )
        
        await state.set_state(BotStates.main_menu)
    
    async def handle_solver_menu(self, callback: CallbackQuery, state: FSMContext):
        """Обработка меню решатора"""
        solver_image_path = self.get_image_path("solver")
        
        solver_text = """
🧮 <b>Решатор задач</b>

<i>Soon...</i>

Функция находится в разработке.
Скоро здесь будет доступен мощный решатор для:

• 📐 Математических задач
• ⚗️ Физических задач  
• 🧪 Химических уравнений
• 📊 Построения графиков

Следите за обновлениями! 🚀
        """
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="back_main")]
        ])
        
        if solver_image_path:
            photo = FSInputFile(solver_image_path)
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=photo,
                caption=solver_text,
                parse_mode=ParseMode.HTML,
                reply_markup=back_keyboard
            )
        else:
            await callback.message.edit_text(
                solver_text,
                parse_mode=ParseMode.HTML,
                reply_markup=back_keyboard
            )
        
        await state.set_state(BotStates.solver_menu)
        await callback.answer()
    
    async def handle_textbooks_menu(self, callback: CallbackQuery, state: FSMContext):
        """Обработка меню учебников"""
        textbooks_image_path = self.get_image_path("textbooks")
        
        textbooks_text = """
📚 <b>Учебники</b>

Выберите класс для поиска учебников:

🎓 Доступны учебники для 1-11 классов
📖 Различные предметы
📄 Высокое качество PDF
⬇️ Быстрое скачивание

Нажмите на класс ниже:
        """
        
        if textbooks_image_path:
            photo = FSInputFile(textbooks_image_path)
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=photo,
                caption=textbooks_text,
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_classes_keyboard()
            )
        else:
            await callback.message.edit_text(
                textbooks_text,
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_classes_keyboard()
            )
        
        await state.set_state(BotStates.selecting_class)
        await callback.answer()
    
    async def handle_class_selection(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора класса"""
        class_num = callback.data.split("_")[1]
        
        subjects_text = f"""
📚 <b>Выбор предмета для {class_num} класса</b>

Выберите предмет для поиска учебников:
        """
        
        await callback.message.edit_text(
            subjects_text,
            parse_mode=ParseMode.HTML,
            reply_markup=self.get_subjects_keyboard(class_num)
        )
        
        await state.update_data(selected_class=class_num)
        await state.set_state(BotStates.selecting_subject)
        await callback.answer()
    
    async def handle_subject_selection(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора предмета"""
        _, class_num, subject = callback.data.split("_", 2)
        
        # Получаем учебники из базы данных
        textbooks = await self.db_manager.get_textbooks_by_class_and_subject(
            class_name=f"{class_num} класс",
            subject=subject
        )
        
        if textbooks:
            textbooks_text = f"""
📖 <b>Учебники по предмету для {class_num} класса</b>

Найдено учебников: {len(textbooks)}

Выберите автора или воспользуйтесь помощью:
            """
            
            # Создаем клавиатуру с учебниками
            keyboard = []
            for book in textbooks[:10]:  # Показываем первые 10
                keyboard.append([InlineKeyboardButton(
                    text=f"📖 {book['author']} - {book['title'][:30]}...",
                    callback_data=f"book_{book['id']}"
                )])
            
            # Добавляем кнопку помощи
            keyboard.append([InlineKeyboardButton(text="❓ Где посмотреть автора?", callback_data="help_author")])
            keyboard.append([InlineKeyboardButton(text="◀️ Назад к предметам", callback_data=f"back_subjects_{class_num}")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        else:
            textbooks_text = f"""
📖 <b>Учебники по предмету для {class_num} класса</b>

К сожалению, учебники для данного предмета пока не найдены.

Попробуйте выбрать другой предмет или обратитесь к администратору.
            """
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад к предметам", callback_data=f"back_subjects_{class_num}")]
            ])
        
        await callback.message.edit_text(
            textbooks_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        await state.update_data(selected_subject=subject)
        await state.set_state(BotStates.viewing_textbooks)
        await callback.answer()
    
    async def handle_author_help(self, callback: CallbackQuery, state: FSMContext):
        """Показ помощи по выбору автора"""
        help_image_path = self.get_image_path("help")
        
        help_text = """
❓ <b>Как найти автора учебника</b>

Автор учебника обычно указан:

1. 📖 На обложке учебника (крупными буквами)
2. 📄 На титульной странице 
3. 🔍 В каталоге библиотеки
4. 💻 На сайте издательства

<i>Обычно автор указывается в формате: Фамилия И.О.</i>

Пример: Мерзляк А.Г., Полонский В.Б.
        """
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к учебникам", callback_data="back_textbooks_help")]
        ])
        
        if help_image_path:
            photo = FSInputFile(help_image_path)
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=photo,
                caption=help_text,
                parse_mode=ParseMode.HTML,
                reply_markup=back_keyboard
            )
        else:
            await callback.message.edit_text(
                help_text,
                parse_mode=ParseMode.HTML,
                reply_markup=back_keyboard
            )
        
        await state.set_state(BotStates.help_mode)
        await callback.answer()
    
    async def handle_navigation(self, callback: CallbackQuery, state: FSMContext):
        """Обработка навигации"""
        if callback.data == "back_main":
            await self.show_main_menu_from_callback(callback, state)
        elif callback.data == "back_classes":
            await self.handle_textbooks_menu(callback, state)
        elif callback.data.startswith("back_subjects_"):
            class_num = callback.data.split("_")[2]
            await self.handle_class_selection(callback, state)
        elif callback.data == "back_textbooks_help":
            # Возвращаемся к учебникам
            state_data = await state.get_data()
            class_num = state_data.get('selected_class', '1')
            subject = state_data.get('selected_subject', 'math')
            callback.data = f"subject_{class_num}_{subject}"
            await self.handle_subject_selection(callback, state)
        
        await callback.answer()
    
    async def callback_handler(self, callback: CallbackQuery, state: FSMContext):
        """Главный обработчик callback-запросов"""
        try:
            if callback.data == "agree_rules":
                await self.handle_rules_agreement(callback, state)
            elif callback.data == "menu_solver":
                await self.handle_solver_menu(callback, state)
            elif callback.data == "menu_textbooks":
                await self.handle_textbooks_menu(callback, state)
            elif callback.data.startswith("class_"):
                await self.handle_class_selection(callback, state)
            elif callback.data.startswith("subject_"):
                await self.handle_subject_selection(callback, state)
            elif callback.data == "help_author":
                await self.handle_author_help(callback, state)
            elif callback.data.startswith("back_"):
                await self.handle_navigation(callback, state)
            elif callback.data.startswith("book_"):
                book_id = callback.data.split("_")[1]
                await self.handle_book_download(callback, book_id)
            else:
                await callback.answer("Функция в разработке")
                
        except Exception as e:
            logging.error(f"Ошибка в callback_handler: {e}")
            await callback.answer("Произошла ошибка")
    
    async def handle_book_download(self, callback: CallbackQuery, book_id: str):
        """Обработка скачивания книги"""
        await callback.answer("📥 Функция скачивания в разработке")
        # Здесь будет логика скачивания книги
    
    def register_handlers(self):
        """Регистрация обработчиков"""
        # Команды
        self.dp.message.register(self.start_command, Command("start"))
        
        # Callback обработчики
        self.dp.callback_query.register(self.callback_handler)
    
    async def start(self):
        """Запуск бота"""
        # Настройка логирования
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("🚀 Запуск улучшенного Telegram бота RUУчебник...")
        
        # Проверка токена
        bot_token = BOT_CONFIG.get('token')
        if not bot_token or bot_token == 'demo_token':
            logger.error("❌ Укажите настоящий токен бота в переменных окружения BOT_TOKEN")
            return
        
        try:
            # Инициализация базы данных
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            
            # Создание бота и диспетчера
            self.bot = Bot(
                token=bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            
            storage = MemoryStorage()
            self.dp = Dispatcher(storage=storage)
            
            # Регистрация обработчиков
            self.register_handlers()
            
            # Проверка подключения
            bot_info = await self.bot.get_me()
            logger.info(f"✅ Бот подключен: @{bot_info.username}")
            
            # Установка команд
            from aiogram.types import BotCommand
            await self.bot.set_my_commands([
                BotCommand(command="start", description="🏠 Начать работу с ботом"),
                BotCommand(command="help", description="❓ Помощь"),
            ])
            
            # Запуск polling
            logger.info("🔄 Запуск polling...")
            await self.dp.start_polling(self.bot, drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}")
        finally:
            if self.db_manager:
                await self.db_manager.close()
            if self.bot:
                await self.bot.session.close()


async def main():
    """Главная функция"""
    bot = EnhancedRUUchebnikBot()
    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"💥 Ошибка запуска: {e}")
        sys.exit(1)