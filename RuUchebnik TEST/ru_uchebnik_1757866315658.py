import sys
import os
import json
import subprocess
import shutil
import time
import threading
import asyncio
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QInputDialog, QTextEdit, QTabWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap
import telegram
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters, ContextTypes, Update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

# Проверка версии библиотеки
try:
    import pkg_resources
    ptb_version = pkg_resources.get_distribution("python-telegram-bot").version
    print(f"Используемая версия python-telegram-bot: {ptb_version}")
    if pkg_resources.parse_version(ptb_version) < pkg_resources.parse_version("20.0"):
        print("Установлена устаревшая версия python-telegram-bot. Обновите до версии 20.0 или выше.")
        sys.exit(1)
except Exception as e:
    print(f"Ошибка при проверке версии: {e}")
    sys.exit(1)

# Определение пути к директории скрипта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Конфигурация приложения
BOT_TOKEN = '8238798012:AAEtdmiVOSta1_ogJTstJSHjtr6aKc8J0Z0'  # Замените на ваш токен
ADMIN_PASSWORD = "14101988"  # Пароль для GUI
ADMIN_ID = 5982787659  # Замените на ID админа Telegram
LOGS_FILE = os.path.join(BASE_DIR, "logs.json")
LOGS_TXT_FILE = os.path.join(BASE_DIR, "logs.txt")
ERRORS_FILE = os.path.join(BASE_DIR, "errors.json")
ERRORS_TXT_FILE = os.path.join(BASE_DIR, "errors.txt")
BAN_LOGS_FILE = os.path.join(BASE_DIR, "ban_logs.json")
BAN_LOGS_TXT_FILE = os.path.join(BASE_DIR, "ban_logs.txt")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
USERS_TXT_FILE = os.path.join(BASE_DIR, "users.txt")
BANNED_FILE = os.path.join(BASE_DIR, "banned.json")
BANNED_TXT_FILE = os.path.join(BASE_DIR, "banned.txt")
TEXTBOOKS_FILE = os.path.join(BASE_DIR, "textbooks.json")
TEXTBOOKS_TXT_FILE = os.path.join(BASE_DIR, "textbooks.txt")
TEXTBOOKS_DIR = os.path.join(BASE_DIR, "textbooks")
UPDATE_INTERVAL = 1000  # Ускоренный интервал обновления

# Глобальные переменные
bot_process = None
bot_status = "Stopped"
bot_app = None
error_logs = []

# Сигналы для мгновенного сохранения
class DataSaveThread(QThread):
    save_signal = pyqtSignal(dict, str)

    def __init__(self):
        super().__init__()
        self.data = {}
        self.file = ""
        self.txt_file = ""

    def run(self):
        save_data(self.file, self.data)
        if self.txt_file:
            save_txt_data(self.txt_file, self.data)

    def save(self, data, file, txt_file=None):
        self.data = data
        self.file = file
        self.txt_file = txt_file
        self.start()

# Функции для работы с данными
def load_data(file):
    """Загружает данные из JSON файла с обработкой ошибок."""
    if os.path.exists(file):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON в {file}: {e}")
            return {}
    return {}

def save_data(file, data):
    """Сохраняет данные в JSON файл мгновенно."""
    os.makedirs(os.path.dirname(file) or '.', exist_ok=True)
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_txt_data(file, data):
    """Сохраняет данные в TXT файл мгновенно."""
    os.makedirs(os.path.dirname(file) or '.', exist_ok=True)
    with open(file, 'w', encoding='utf-8') as f:
        if isinstance(data, dict):
            for key, value in data.items():
                f.write(f"{key}: {json.dumps(value)}\n")
        elif isinstance(data, list):
            for item in data:
                f.write(f"{item}\n")

def update_bot_status():
    """Обновляет статус бота в реальном времени."""
    global bot_status
    if bot_process and bot_process.poll() is None:
        bot_status = "Running"
    else:
        bot_status = "Stopped"

# Класс админ панели GUI
class RUUchebnikAdmin(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RUУчебник - Админ Панель")
        self.setFixedSize(400, 600)
        self.setStyleSheet("background-color: #001F3F;")

        # Инициализация данных
        self.logs = load_data(LOGS_FILE)
        self.error_logs = load_data(ERRORS_FILE)
        self.ban_logs = load_data(BAN_LOGS_FILE)
        self.users = load_data(USERS_FILE)
        self.banned_users = load_data(BANNED_FILE)
        self.textbooks = load_data(TEXTBOOKS_FILE)
        self.bot_running = False
        self.save_thread = DataSaveThread()

        # Виджет логотипа
        self.logo_widget = QWidget(self)
        self.logo_widget.setStyleSheet("background-color: #001F3F;")
        self.logo_label = QLabel("RUУчебник", self.logo_widget)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setFont(QFont("Arial", 40, QFont.Weight.Bold))
        self.logo_label.setStyleSheet("color: white;")
        logo_layout = QVBoxLayout(self.logo_widget)
        logo_layout.addWidget(self.logo_label)
        self.logo_widget.setGeometry(0, 0, 400, 600)

        # Виджет ввода пароля
        self.password_widget = QWidget(self)
        self.password_widget.setStyleSheet("background-color: #808080; border-radius: 10px;")
        password_layout = QVBoxLayout(self.password_widget)
        password_label = QLabel("Введите пароль:", self.password_widget)
        password_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        password_label.setFont(QFont("Arial", 14))
        password_label.setStyleSheet("color: white;")
        self.password_input = QLineEdit(self.password_widget)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("background-color: white; border: 1px solid gray; border-radius: 5px;")
        password_button = QPushButton("Войти", self.password_widget)
        password_button.setStyleSheet("background-color: #D3D3D3; color: black; border-radius: 5px; padding: 5px;")
        password_button.clicked.connect(self.check_password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        password_layout.addWidget(password_button)
        self.password_widget.setGeometry(0, 600, 400, 200)

        # Основная панель с вкладками
        self.main_widget = QWidget(self)
        self.main_widget.setStyleSheet("background-color: #808080; border-radius: 10px;")
        main_layout = QVBoxLayout(self.main_widget)
        self.status_label = QLabel("", self.main_widget)
        self.status_label.setStyleSheet("color: white; font-size: 12px;")
        self.status_label.setFixedSize(20, 20)
        main_layout.addWidget(self.status_label)
        self.tab_widget = QTabWidget(self.main_widget)
        self.control_tab = QWidget()
        self.logs_tab = QWidget()
        self.ban_tab = QWidget()

        # Вкладка управления
        control_layout = QVBoxLayout(self.control_tab)
        buttons = [
            ("Запустить бота", self.start_bot),
            ("Остановить бота", self.stop_bot),
            ("Скачать общие логи", lambda: self.download_logs_type(LOGS_FILE, LOGS_TXT_FILE, "Общие логи")),
            ("Скачать логи ошибок", lambda: self.download_logs_type(ERRORS_FILE, ERRORS_TXT_FILE, "Логи ошибок")),
            ("Скачать логи бана", lambda: self.download_logs_type(BAN_LOGS_FILE, BAN_LOGS_TXT_FILE, "Логи бана")),
            ("Сохранить пользователей", lambda: self.save_data_type(USERS_FILE, USERS_TXT_FILE, "Пользователи")),
            ("Сохранить баны", lambda: self.save_data_type(BANNED_FILE, BANNED_TXT_FILE, "Баны")),
            ("Сохранить учебники", lambda: self.save_data_type(TEXTBOOKS_FILE, TEXTBOOKS_TXT_FILE, "Учебники")),
            ("Посмотреть пользователей", self.view_users),
            ("Забанить пользователя", self.ban_user),
            ("Разбанить пользователя", self.unban_user),
            ("Добавить учебник", self.add_textbook),
            ("Удалить учебник", self.remove_textbook),
            ("Добавить новый класс", self.add_new_class),
            ("Удалить класс", self.delete_class),
            ("Добавить новый предмет", self.add_new_subject),
            ("Отправить рассылку", self.send_broadcast),
            ("Просмотреть статистику", self.view_stats),
            ("Выход", self.close_app)
        ]
        for text, func in buttons:
            button = QPushButton(text, self.control_tab)
            button.setStyleSheet("background-color: #D3D3D3; color: black; border-radius: 5px; padding: 10px;")
            button.clicked.connect(func)
            control_layout.addWidget(button)

        # Вкладка логов
        logs_layout = QVBoxLayout(self.logs_tab)
        self.log_download_buttons = [
            ("Скачать общие логи", lambda: self.download_logs_type(LOGS_FILE, LOGS_TXT_FILE, "Общие логи")),
            ("Скачать логи ошибок", lambda: self.download_logs_type(ERRORS_FILE, ERRORS_TXT_FILE, "Логи ошибок")),
            ("Скачать логи бана", lambda: self.download_logs_type(BAN_LOGS_FILE, BAN_LOGS_TXT_FILE, "Логи бана"))
        ]
        for text, func in self.log_download_buttons:
            button = QPushButton(text, self.logs_tab)
            button.setStyleSheet("background-color: #D3D3D3; color: black; border-radius: 5px; padding: 10px;")
            button.clicked.connect(func)
            logs_layout.addWidget(button)

        # Вкладка банов
        ban_layout = QVBoxLayout(self.ban_tab)
        self.ban_list = QTextEdit(self.ban_tab)
        self.ban_list.setReadOnly(True)
        ban_layout.addWidget(self.ban_list)
        self.update_ban_list()

        self.tab_widget.addTab(self.control_tab, "Управление")
        self.tab_widget.addTab(self.logs_tab, "Логи")
        self.tab_widget.addTab(self.ban_tab, "Баны")
        main_layout.addWidget(self.tab_widget)
        self.main_widget.setGeometry(0, -400, 400, 500)

        # Анимации
        self.logo_anim = QPropertyAnimation(self.logo_widget, b"geometry")
        self.password_anim = QPropertyAnimation(self.password_widget, b"geometry")
        self.main_anim = QPropertyAnimation(self.main_widget, b"geometry")

        # Таймер
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(UPDATE_INTERVAL)

        self.show_logo()

    def show_logo(self):
        """Показать логотип."""
        self.logo_anim.setDuration(500)
        start_geom = QRect(0, 0, 400, 600)
        end_geom = start_geom
        self.logo_anim.setStartValue(start_geom)
        self.logo_anim.setEndValue(end_geom)
        self.logo_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.logo_anim.start()
        self.logo_anim.finished.connect(self.show_password_panel)

    def show_password_panel(self):
        """Открыть панель пароля."""
        self.password_anim.setDuration(300)
        start_geom = QRect(0, 200, 400, 200)
        end_geom = QRect(0, 200, 400, 200)
        self.password_anim.setStartValue(start_geom.adjusted(0, -100, 0, -100))
        self.password_anim.setEndValue(end_geom)
        self.password_anim.setEasingCurve(QEasingCurve.Type.OutBounce)
        self.password_anim.start()

    def check_password(self):
        """Проверить пароль."""
        if self.password_input.text() == ADMIN_PASSWORD:
            self.password_anim.setDuration(300)
            start_geom = self.password_widget.geometry()
            end_geom = QRect(0, 600, 400, 200)
            self.password_anim.setStartValue(start_geom)
            self.password_anim.setEndValue(end_geom)
            self.password_anim.setEasingCurve(QEasingCurve.Type.InQuad)
            self.password_anim.start()
            self.password_anim.finished.connect(self.show_main_panel)
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный пароль.")

    def show_main_panel(self):
        """Открыть основную панель."""
        self.main_anim.setDuration(300)
        start_geom = QRect(0, 200, 400, 500)
        end_geom = QRect(0, 0, 400, 600)
        self.main_anim.setStartValue(start_geom)
        self.main_anim.setEndValue(end_geom)
        self.main_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.main_anim.start()

    def start_bot(self):
        """Запустить бота."""
        global bot_process, bot_app
        if bot_process is None or bot_process.poll() is None:
            if not BOT_TOKEN or 'YOUR_BOT_TOKEN' in BOT_TOKEN:
                self.error_logs.append(f"Ошибка: Токен не настроен в {datetime.now()}")
                self.save_all_data()
                QMessageBox.critical(self, "Ошибка", "Настройте BOT_TOKEN.")
                return
            try:
                bot_process = subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "ru_uchebnik.py"), "--bot-only"], cwd=BASE_DIR)
                self.logs.append(f"Бот запущен в {datetime.now()}")
                self.save_all_data()
                self.update_status()
                QMessageBox.information(self, "Успех", "Бот запущен!")
                bot_app = Application.builder().token(BOT_TOKEN).build()
                self.setup_bot_handlers()
                threading.Thread(target=self.run_bot_polling, daemon=True).start()
            except Exception as e:
                self.error_logs.append(f"Ошибка запуска: {str(e)} в {datetime.now()}")
                self.save_all_data()
                QMessageBox.critical(self, "Ошибка", f"Ошибка: {str(e)}")
        else:
            QMessageBox.warning(self, "Предупреждение", "Бот уже запущен.")

    def stop_bot(self):
        """Остановить бота."""
        global bot_process, bot_app
        if bot_process and bot_process.poll() is None:
            users = load_data(USERS_FILE)
            bot = Bot(token=BOT_TOKEN)
            for user_id in users:
                try:
                    bot.send_message(chat_id=user_id, text="Бот на технических работах.")
                except TelegramError as e:
                    self.logs.append(f"Ошибка рассылки для {user_id}: {str(e)}")
            bot_process.terminate()
            bot_process = None
            bot_app = None
            self.logs.append(f"Бот остановлен в {datetime.now()}")
            self.save_all_data()
            self.update_status()
            QMessageBox.information(self, "Успех", "Бот остановлен.")
        else:
            QMessageBox.warning(self, "Предупреждение", "Бот уже остановлен.")

    def update_status(self):
        """Обновить статус бота."""
        update_bot_status()
        pixmap = QPixmap(20, 20)
        if bot_status == "Running":
            pixmap.fill(QColor("green"))
        else:
            pixmap.fill(QColor("red"))
        self.status_label.setPixmap(pixmap)

    def download_logs_type(self, json_file, txt_file, title):
        """Скачать логи."""
        data = load_data(json_file)
        if not data:
            QMessageBox.warning(self, "Ошибка", f"{title} пусты.")
            return
        json_path, _ = QFileDialog.getSaveFileName(self, f"Сохранить {title} (JSON)", "", "JSON Files (*.json)")
        txt_path, _ = QFileDialog.getSaveFileName(self, f"Сохранить {title} (TXT)", "", "Text Files (*.txt)")
        if json_path:
            save_data(json_path, data)
        if txt_path:
            save_txt_data(txt_path, data)
        QMessageBox.information(self, "Успех", f"{title} сохранены.")

    def save_data_type(self, json_file, txt_file, title):
        """Сохранить данные."""
        data = load_data(json_file)
        if not data:
            QMessageBox.warning(self, "Ошибка", f"{title} пусты.")
            return
        json_path, _ = QFileDialog.getSaveFileName(self, f"Сохранить {title} (JSON)", "", "JSON Files (*.json)")
        txt_path, _ = QFileDialog.getSaveFileName(self, f"Сохранить {title} (TXT)", "", "Text Files (*.txt)")
        if json_path:
            save_data(json_path, data)
        if txt_path:
            save_txt_data(txt_path, data)
        QMessageBox.information(self, "Успех", f"{title} сохранены.")

    def view_users(self):
        """Показать пользователей."""
        user_list = "\n".join([f"{data['username']} (ID: {uid}, Скачиваний: {data.get('downloads', 0)})" for uid, data in self.users.items()])
        QMessageBox.information(self, "Список пользователей", user_list or "Нет пользователей.")

    def ban_user(self):
        """Забанить пользователя."""
        user_id, ok = QInputDialog.getText(self, "Бан пользователя", "Введите ID:")
        if ok and user_id:
            if user_id not in self.users:
                QMessageBox.warning(self, "Ошибка", "Пользователь не найден.")
                return
            reason, ok = QInputDialog.getText(self, "Причина", "Введите причину:")
            if ok:
                days, ok = QInputDialog.getInt(self, "Срок", "Дни:", 15, 1, 365)
                if ok:
                    until = datetime.now() + timedelta(days=days)
                    self.banned_users[user_id] = {"reason": reason, "until": str(until)}
                    self.ban_logs.append(f"Бан {user_id} на {days} дней. Причина: {reason} в {datetime.now()}")
                    self.logs.append(f"Бан {user_id}")
                    self.save_all_data()
                    self.update_ban_list()
                    QMessageBox.information(self, "Успех", f"Бан {user_id}.")

    def unban_user(self):
        """Разбанить пользователя."""
        if not self.banned_users:
            QMessageBox.warning(self, "Ошибка", "Нет забаненных.")
            return
        user_id, ok = QInputDialog.getText(self, "Разбан", "Введите ID:")
        if ok and user_id in self.banned_users:
            del self.banned_users[user_id]
            self.ban_logs.append(f"Разбан {user_id} в {datetime.now()}")
            self.logs.append(f"Разбан {user_id}")
            self.save_all_data()
            self.update_ban_list()
            QMessageBox.information(self, "Успех", f"Разбан {user_id}.")
        else:
            QMessageBox.warning(self, "Ошибка", "ID не найден.")

    def update_ban_list(self):
        """Обновить список банов."""
        self.ban_list.clear()
        for uid, data in self.banned_users.items():
            self.ban_list.append(f"ID: {uid}, Причина: {data['reason']}, До: {data['until']}")

    def add_textbook(self):
        """Добавить учебник."""
        class_, ok = QInputDialog.getText(self, "Класс", "Введите класс:")
        if ok:
            subject, ok = QInputDialog.getText(self, "Предмет", "Введите предмет:")
            if ok:
                author, ok = QInputDialog.getText(self, "Автор", "Введите автора:")
                if ok:
                    file, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF Files (*.pdf)")
                    if file and os.path.exists(file):
                        dest = os.path.join(TEXTBOOKS_DIR, os.path.basename(file))
                        os.makedirs(TEXTBOOKS_DIR, exist_ok=True)
                        shutil.copy(file, dest)
                        if class_ not in self.textbooks:
                            self.textbooks[class_] = {}
                        if subject not in self.textbooks[class_]:
                            self.textbooks[class_][subject] = {}
                        if author not in self.textbooks[class_][subject]:
                            self.textbooks[class_][subject][author] = []
                        self.textbooks[class_][subject][author].append(dest)
                        self.logs.append(f"Учебник: {class_} - {subject} - {author}")
                        self.save_all_data()
                        QMessageBox.information(self, "Успех", "Учебник добавлен!")
                    else:
                        QMessageBox.warning(self, "Ошибка", "Неверный файл.")

    def add_new_class(self):
        """Добавить новый класс."""
        class_, ok = QInputDialog.getText(self, "Новый класс", "Введите номер класса (например, 10):")
        if ok:
            if class_ in self.textbooks:
                QMessageBox.warning(self, "Ошибка", "Класс уже существует.")
                return
            self.textbooks[class_] = {}
            self.logs.append(f"Новый класс добавлен: {class_} в {datetime.now()}")
            self.save_all_data()
            QMessageBox.information(self, "Успех", f"Всё, я добавил класс {class_}! Теперь добавьте предметы и учебники.")

    def delete_class(self):
        """Удалить класс."""
        classes = list(self.textbooks.keys())
        if not classes:
            QMessageBox.warning(self, "Ошибка", "Нет классов для удаления.")
            return
        class_, ok = QInputDialog.getItem(self, "Удалить класс", "Выберите класс:", classes, 0, False)
        if ok and class_ in self.textbooks:
            for subject in self.textbooks[class_]:
                for author in self.textbooks[class_][subject]:
                    for file_path in self.textbooks[class_][subject][author]:
                        if os.path.exists(file_path):
                            os.remove(file_path)
            del self.textbooks[class_]
            self.logs.append(f"Класс {class_} удалён в {datetime.now()}")
            self.save_all_data()
            QMessageBox.information(self, "Успех", f"Класс {class_} и все связанные учебники удалены.")

    def add_new_subject(self):
        """Добавить новый предмет."""
        classes = list(self.textbooks.keys())
        if not classes:
            QMessageBox.warning(self, "Ошибка", "Нет классов для добавления предмета.")
            return
        class_, ok = QInputDialog.getItem(self, "Класс", "Выберите класс:", classes, 0, False)
        if ok and class_ in self.textbooks:
            subject, ok = QInputDialog.getText(self, "Новый предмет", "Введите название предмета (например, Немецкий):")
            if ok:
                if subject in self.textbooks[class_]:
                    QMessageBox.warning(self, "Ошибка", "Предмет уже существует.")
                    return
                self.textbooks[class_][subject] = {}
                self.logs.append(f"Новый предмет добавлен: {class_} - {subject} в {datetime.now()}")
                self.save_all_data()
                QMessageBox.information(self, "Успех", f"Всё, я добавил {subject}! Теперь добавьте учебник для этого предмета.")
                # Заново открыть меню добавления учебника
                self.add_textbook()

    def remove_textbook(self):
        """Удалить учебник."""
        classes = list(self.textbooks.keys())
        if not classes:
            QMessageBox.warning(self, "Ошибка", "Нет учебников для удаления.")
            return
        class_, ok = QInputDialog.getItem(self, "Класс", "Выберите класс:", classes, 0, False)
        if ok and class_ in self.textbooks:
            subjects = list(self.textbooks[class_].keys())
            if not subjects:
                del self.textbooks[class_]
                self.save_all_data()
                QMessageBox.information(self, "Успех", f"Все учебники класса {class_} удалены.")
                return
            subject, ok = QInputDialog.getItem(self, "Предмет", "Выберите предмет:", subjects, 0, False)
            if ok and subject in self.textbooks[class_]:
                authors = list(self.textbooks[class_][subject].keys())
                if not authors:
                    del self.textbooks[class_][subject]
                    self.save_all_data()
                    QMessageBox.information(self, "Успех", f"Все учебники предмета {subject} удалены.")
                    return
                author, ok = QInputDialog.getItem(self, "Автор", "Выберите автора:", authors, 0, False)
                if ok and author in self.textbooks[class_][subject]:
                    textbooks = self.textbooks[class_][subject][author]
                    if not textbooks:
                        del self.textbooks[class_][subject][author]
                        self.save_all_data()
                        QMessageBox.information(self, "Успех", f"Все учебники автора {author} удалены.")
                        return
                    textbook_list = [os.path.basename(f) for f in textbooks]
                    textbook, ok = QInputDialog.getItem(self, "Учебник", "Выберите учебник для удаления:", textbook_list, 0, False)
                    if ok:
                        file_path = textbooks[textbook_list.index(textbook)]
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        textbooks.remove(file_path)
                        if not textbooks:
                            del self.textbooks[class_][subject][author]
                        if not self.textbooks[class_][subject]:
                            del self.textbooks[class_][subject]
                        if not self.textbooks[class_]:
                            del self.textbooks[class_]
                        self.logs.append(f"Удалён учебник: {class_} - {subject} - {author} - {textbook}")
                        self.save_all_data()
                        QMessageBox.information(self, "Успех", f"Учебник {textbook} удалён.")

    def send_broadcast(self):
        """Отправить рассылку."""
        message, ok = QInputDialog.getText(self, "Рассылка", "Сообщение:")
        if ok:
            file, _ = QFileDialog.getOpenFileName(self, "Медиа", "", "Images (*.jpg *.png);;All Files (*)")
            bot = Bot(token=BOT_TOKEN)
            users = load_data(USERS_FILE)
            for user_id in users:
                try:
                    if file and os.path.exists(file):
                        with open(file, 'rb') as f:
                            bot.send_photo(chat_id=user_id, photo=f, caption=message)
                    else:
                        bot.send_message(chat_id=user_id, text=message)
                    self.logs.append(f"Рассылка для {user_id}")
                except TelegramError as e:
                    self.logs.append(f"Ошибка рассылки для {user_id}: {str(e)}")
            self.save_all_data()
            QMessageBox.information(self, "Успех", "Рассылка завершена.")

    def view_stats(self):
        """Показать статистику."""
        total_users = len(self.users)
        total_downloads = sum(user.get('downloads', 0) for user in self.users.values())
        stats = f"Пользователей: {total_users}\nСкачиваний: {total_downloads}"
        QMessageBox.information(self, "Статистика", stats)

    def save_all_data(self):
        """Сохранить все данные."""
        self.save_thread.save(self.logs, LOGS_FILE, LOGS_TXT_FILE)
        self.save_thread.save(self.error_logs, ERRORS_FILE, ERRORS_TXT_FILE)
        self.save_thread.save(self.ban_logs, BAN_LOGS_FILE, BAN_LOGS_TXT_FILE)
        self.save_thread.save(self.users, USERS_FILE, USERS_TXT_FILE)
        self.save_thread.save(self.banned_users, BANNED_FILE, BANNED_TXT_FILE)
        self.save_thread.save(self.textbooks, TEXTBOOKS_FILE, TEXTBOOKS_TXT_FILE)

    def close_app(self):
        """Закрыть приложение."""
        self.stop_bot()
        self.save_all_data()
        QMessageBox.information(self, "Выход", "Приложение закрыто.")
        self.close()

    def closeEvent(self, event):
        """Обработка закрытия."""
        self.stop_bot()
        self.save_all_data()
        event.accept()

    def setup_bot_handlers(self):
        """Настройка обработчиков бота."""
        global bot_app
        if not bot_app:
            return

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            user = update.effective_user
            user_id = user.id
            if user_id not in self.users:
                self.users[user_id] = {"username": user.username, "joined": datetime.now(), "downloads": 0, "agreed": False}
                self.logs.append(f"Новый пользователь {user.username} ({user_id}) в {datetime.now()}")
                self.save_all_data()
            if not self.users[user_id]["agreed"]:
                rules_text = (
                    "<b><font color='red'>Правила RUУчебник</font></b>\n\n"
                    "• Нельзя флудить.\n"
                    "• Нельзя ломать бот.\n"
                    "Нажмите кнопку ниже для согласия."
                )
                keyboard = [[InlineKeyboardButton("Да, я принимаю ответственность", callback_data="agree")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                msg = await update.message.reply_text(rules_text, parse_mode='HTML', reply_markup=reply_markup)
                context.user_data[user_id] = {"message_id": msg.message_id}
            else:
                await self.show_main_menu(update, context)

        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            user_id = update.effective_user.id
            if user_id not in self.users or not self.users[user_id]["agreed"]:
                await update.message.reply_text("Согласитесь с правилами через /start.")
                return

        async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            query = update.callback_query
            await query.answer()
            user_id = query.from_user.id
            if user_id not in self.users:
                await query.edit_message_text("Начните с /start.")
                return
            data = query.data
            if data == "agree":
                self.users[user_id]["agreed"] = True
                self.logs.append(f"Пользователь {user_id} согласился в {datetime.now()}")
                self.save_all_data()
                msg_id = context.user_data.get(user_id, {}).get("message_id")
                if msg_id:
                    try:
                        await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
                    except TelegramError:
                        pass
                del context.user_data[user_id]
                await self.show_main_menu(update, context)
            elif data == "textbook":
                keyboard = []
                for i in range(1, 10, 3):
                    row = []
                    for j in range(3):
                        if i + j <= 9:
                            row.append(InlineKeyboardButton(f"{i+j} класс", callback_data=f"class_{i+j}"))
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("Назад", callback_data="back")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("Выберите класс:", reply_markup=reply_markup)
            elif data.startswith("class_"):
                class_ = int(data.split("_")[1])
                subjects = list(self.textbooks.get(str(class_), {}).keys()) if self.textbooks.get(str(class_)) else []
                keyboard = []
                for subject in subjects:
                    keyboard.append([InlineKeyboardButton(subject, callback_data=f"subject_{class_}_{subject}")])
                keyboard.append([InlineKeyboardButton("Назад", callback_data="back")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("Выберите предмет:", reply_markup=reply_markup)
            elif data.startswith("subject_"):
                _, class_, subject = data.split("_")
                authors = list(self.textbooks.get(str(class_), {}).get(subject, {}).keys()) if self.textbooks.get(str(class_), {}).get(subject) else []
                keyboard = []
                for author in authors:
                    keyboard.append([InlineKeyboardButton(author, callback_data=f"author_{class_}_{subject}_{author}")])
                keyboard.append([InlineKeyboardButton("Назад", callback_data="back")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("Выберите автора:", reply_markup=reply_markup)
            elif data.startswith("author_"):
                _, class_, subject, author = data.split("_")
                textbooks = self.textbooks.get(str(class_), {}).get(subject, {}).get(author, [])
                if textbooks and all(os.path.exists(f) for f in textbooks):
                    waiting_msg = await query.message.reply_text("Подождите, я загружаю учебник...")
                    await asyncio.sleep(1)  # Имитация загрузки
                    textbook_list = [os.path.basename(f) for f in textbooks]
                    textbook, ok = await context.bot.send_poll(chat_id=user_id, question="Выберите учебник:", options=textbook_list, is_anonymous=False)
                    selected_textbook = textbook_list[0]  # По умолчанию первый, можно улучшить с обработкой ответа пользователя
                    file_path = textbooks[textbook_list.index(selected_textbook)]
                    with open(file_path, 'rb') as f:
                        await query.message.reply_document(document=f, caption="Удачного использования RuУчебник!")
                    self.users[user_id]["downloads"] += 1
                    self.logs.append(f"{self.users[user_id]['username']} скачал {class_} - {subject} - {author} - {selected_textbook}")
                    self.save_all_data()
                    await context.bot.delete_message(chat_id=user_id, message_id=waiting_msg.message_id)
                    keyboard = [[InlineKeyboardButton("Назад", callback_data="back")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text("Выберите действие:", reply_markup=reply_markup)
                else:
                    await query.edit_message_text("Учебники не найдены.")
                await query.message.delete()
            elif data == "resolver":
                await query.edit_message_text("Soon... 💻")
            elif data == "back":
                await self.show_main_menu(update, context)
            elif user_id == ADMIN_ID:
                if data == "ban":
                    await query.edit_message_text("Введите ID для бана через сообщение.")
                    context.user_data["admin_state"] = "await_ban_id"
                elif data == "unban":
                    await query.edit_message_text("Введите ID для разбана через сообщение.")
                    context.user_data["admin_state"] = "await_unban_id"
                elif data == "stats":
                    total_users = len(self.users)
                    total_downloads = sum(user.get('downloads', 0) for user in self.users.values())
                    await query.edit_message_text(f"Пользователей: {total_users}\nСкачиваний: {total_downloads}")
                elif data == "logs":
                    await query.edit_message_text("\n".join(self.logs[-10:]) or "Логи пусты.")

        async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            user_id = update.effective_user.id
            if user_id != ADMIN_ID:
                return
            state = context.user_data.get("admin_state")
            if state == "await_ban_id":
                ban_id = update.message.text
                if ban_id in self.users:
                    await update.message.reply_text("Введите причину бана:")
                    context.user_data["admin_state"] = "await_ban_reason"
                    context.user_data["ban_user_id"] = ban_id
                else:
                    await update.message.reply_text("Пользователь не найден.")
                    del context.user_data["admin_state"]
            elif state == "await_ban_reason":
                reason = update.message.text
                ban_id = context.user_data["ban_user_id"]
                days = 15  # По умолчанию
                until = datetime.now() + timedelta(days=days)
                self.banned_users[ban_id] = {"reason": reason, "until": str(until)}
                self.ban_logs.append(f"Бан {ban_id} на {days} дней. Причина: {reason} в {datetime.now()}")
                self.logs.append(f"Бан {ban_id}")
                self.save_all_data()
                await update.message.reply_text(f"Бан {ban_id} применён.")
                del context.user_data["admin_state"]
                del context.user_data["ban_user_id"]
            elif state == "await_unban_id":
                unban_id = update.message.text
                if unban_id in self.banned_users:
                    del self.banned_users[unban_id]
                    self.ban_logs.append(f"Разбан {unban_id} в {datetime.now()}")
                    self.logs.append(f"Разбан {unban_id}")
                    self.save_all_data()
                    await update.message.reply_text(f"Разбан {unban_id}.")
                else:
                    await update.message.reply_text("Пользователь не забанен.")
                del context.user_data["admin_state"]

        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
        bot_app.add_handler(CallbackQueryHandler(button))

    def run_bot_polling(self):
        """Запуск опроса бота."""
        global bot_app
        if bot_app:
            bot_app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    if not os.path.exists(os.path.join(BASE_DIR, "ru_uchebnik.py")):
        print(f"Ошибка: Скрипт должен быть ru_uchebnik.py в {BASE_DIR}.")
        sys.exit(1)
    app = QApplication(sys.argv)
    window = RUUchebnikAdmin()
    window.show()
    sys.exit(app.exec())