import os
from typing import Optional

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8238798012:AAEtdmiVOSta1_ogJTstJSHjtr6aKc8J0Z0")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5982787659"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "14101988")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# File Storage Configuration
TEXTBOOKS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "textbooks")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Bot Settings
RULES_TEXT = """
<b><font color='red'>Правила RUУчебник</font></b>

• Нельзя флудить.
• Нельзя ломать бот.
• Используйте бот только для поиска учебников.
• Запрещены оскорбления и спам.

Нажмите кнопку ниже для согласия с правилами.
"""

HELP_TEXT = """
🤖 <b>RUУчебник - Помощник по учебникам</b>

📚 <b>Доступные команды:</b>
/start - Начать работу с ботом
/help - Показать это сообщение
/textbooks - Найти учебники по классам и предметам

📖 <b>Как пользоваться:</b>
1. Нажмите "Учебники" в главном меню
2. Выберите класс (1-11)
3. Выберите предмет
4. Скачайте нужный учебник

⚠️ <b>Правила:</b>
• Не флудите в боте
• Используйте бот по назначению
• Соблюдайте культуру общения

📞 <b>Поддержка:</b>
По вопросам работы бота обращайтесь к администратору.
"""

ABOUT_TEXT = """
📖 <b>О RUУчебник</b>

RUУчебник - это образовательный бот для поиска и скачивания школьных учебников.

🎯 <b>Цель проекта:</b>
Предоставить бесплатный доступ к качественным учебникам для школьников и учителей.

📚 <b>Библиотека содержит:</b>
• Учебники для 1-11 классов
• Все основные предметы
• Актуальные издания
• PDF формат для удобства

👨‍💻 <b>Разработка:</b>
Бот разработан специально для российских школьников.

📊 <b>Статистика:</b>
• Пользователей: {total_users}
• Учебников: {total_textbooks}
• Скачиваний: {total_downloads}

Версия: 1.0.0
© 2024 RUУчебник Bot
"""

# Error Messages
ERROR_MESSAGES = {
    "not_agreed": "⚠️ Сначала согласитесь с правилами через /start",
    "banned": "🚫 Вы заблокированы в боте.\nПричина: {reason}\nДо: {until}",
    "file_not_found": "❌ Файл не найден или был удален",
    "no_textbooks": "📚 В данном разделе пока нет учебников",
    "download_error": "❌ Ошибка при скачивании файла. Попробуйте позже.",
    "general_error": "❌ Произошла ошибка. Попробуйте позже.",
}

# Success Messages
SUCCESS_MESSAGES = {
    "download_started": "📥 Начинаю скачивание...",
    "rules_accepted": "✅ Правила приняты! Добро пожаловать в RUУчебник!",
}

# Inline Keyboard Texts
KEYBOARD_TEXTS = {
    "agree_rules": "Да, я принимаю ответственность",
    "main_menu": "🏠 Главное меню",
    "textbooks": "📚 Учебники",
    "help": "❓ Помощь",
    "about": "ℹ️ О боте",
    "back": "⬅️ Назад",
    "download": "📥 Скачать",
    "soon": "🔜 Soon...",
}

# Classes and Subjects
CLASSES = {
    "1": "1 класс",
    "2": "2 класс", 
    "3": "3 класс",
    "4": "4 класс",
    "5": "5 класс",
    "6": "6 класс",
    "7": "7 класс",
    "8": "8 класс",
    "9": "9 класс",
    "10": "10 класс",
    "11": "11 класс",
}

SUBJECTS = {
    "mathematics": "Математика",
    "russian": "Русский язык",
    "literature": "Литература",
    "english": "Английский язык",
    "history": "История",
    "geography": "География",
    "biology": "Биология",
    "chemistry": "Химия",
    "physics": "Физика",
    "informatics": "Информатика",
    "social_studies": "Обществознание",
    "economics": "Экономика",
    "law": "Право",
    "art": "Изобразительное искусство",
    "music": "Музыка",
    "physical_education": "Физическая культура",
    "technology": "Технология",
    "life_safety": "ОБЖ",
}

# Admin Commands
ADMIN_COMMANDS = {
    "/stats": "Статистика бота",
    "/users": "Список пользователей",
    "/broadcast": "Рассылка сообщений",
    "/ban": "Заблокировать пользователя",
    "/unban": "Разблокировать пользователя",
    "/logs": "Показать логи",
    "/backup": "Создать резервную копию",
}
