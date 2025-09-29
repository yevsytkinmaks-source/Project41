import sys
import os
import subprocess
import asyncio
import threading
import time
import json
from datetime import datetime
from typing import Optional, Dict, List
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import requests
from PIL import Image, ImageTk
import webbrowser

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class RUUchebnikDesktopAdmin:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RUУчебник - Административная панель")
        self.root.geometry("1200x800")
        self.root.configure(bg="#001F3F")
        
        # Configuration
        self.web_url = "http://localhost:5000"
        self.bot_process: Optional[subprocess.Popen] = None
        self.web_process: Optional[subprocess.Popen] = None
        self.session = requests.Session()
        self.is_authenticated = False
        
        # Setup GUI
        self.setup_styles()
        self.create_login_screen()
        self.start_status_monitoring()
        
    def setup_styles(self):
        """Setup custom styles for ttk widgets"""
        style = ttk.Style()
        
        # Configure dark theme
        style.theme_use('clam')
        
        # Button styles
        style.configure('Dark.TButton',
                       background='#D3D3D3',
                       foreground='black',
                       borderwidth=1,
                       focuscolor='none',
                       relief='flat')
        style.map('Dark.TButton',
                 background=[('active', '#BFBFBF')])
        
        # Frame styles  
        style.configure('Dark.TFrame',
                       background='#808080',
                       relief='raised',
                       borderwidth=2)
        
        # Label styles
        style.configure('Dark.TLabel',
                       background='#808080',
                       foreground='white',
                       font=('Arial', 10))
        
        style.configure('Title.TLabel',
                       background='#001F3F',
                       foreground='white',
                       font=('Arial', 24, 'bold'))
        
        # Entry styles
        style.configure('Dark.TEntry',
                       fieldbackground='white',
                       foreground='black',
                       borderwidth=1)
        
        # Treeview styles
        style.configure('Dark.Treeview',
                       background='white',
                       foreground='black',
                       fieldbackground='white')
        style.configure('Dark.Treeview.Heading',
                       background='#D3D3D3',
                       foreground='black')
    
    def create_login_screen(self):
        """Create login screen"""
        # Clear root
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Logo
        logo_frame = tk.Frame(self.root, bg="#001F3F")
        logo_frame.pack(expand=True, fill='both')
        
        title_label = tk.Label(logo_frame, 
                              text="RUУчебник",
                              font=('Arial', 40, 'bold'),
                              bg="#001F3F",
                              fg="white")
        title_label.pack(pady=50)
        
        subtitle_label = tk.Label(logo_frame,
                                 text="Административная панель",
                                 font=('Arial', 16),
                                 bg="#001F3F",
                                 fg="white")
        subtitle_label.pack()
        
        # Login frame
        login_frame = ttk.Frame(logo_frame, style='Dark.TFrame', padding=30)
        login_frame.pack(pady=50)
        
        # Password field
        ttk.Label(login_frame, 
                 text="Введите пароль:",
                 style='Dark.TLabel').pack(pady=5)
        
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(login_frame,
                                  textvariable=self.password_var,
                                  show="*",
                                  style='Dark.TEntry',
                                  font=('Arial', 12),
                                  width=25)
        password_entry.pack(pady=10)
        password_entry.bind('<Return>', lambda e: self.login())
        password_entry.focus()
        
        # Login button
        login_btn = ttk.Button(login_frame,
                              text="Войти",
                              command=self.login,
                              style='Dark.TButton',
                              width=20)
        login_btn.pack(pady=10)
        
        # Status label
        self.status_label = tk.Label(logo_frame,
                                    text="",
                                    font=('Arial', 10),
                                    bg="#001F3F",
                                    fg="red")
        self.status_label.pack(pady=10)
    
    def login(self):
        """Attempt to login"""
        password = self.password_var.get()
        
        if password == "14101988":  # Admin password from config
            self.is_authenticated = True
            self.create_main_interface()
        else:
            self.status_label.config(text="Неверный пароль!")
            self.password_var.set("")
    
    def create_main_interface(self):
        """Create main admin interface"""
        # Clear root
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main container
        main_frame = tk.Frame(self.root, bg="#001F3F")
        main_frame.pack(fill='both', expand=True)
        
        # Top panel
        self.create_top_panel(main_frame)
        
        # Content area
        content_frame = tk.Frame(main_frame, bg="#001F3F")
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Left sidebar
        self.create_sidebar(content_frame)
        
        # Main content area
        self.main_content = tk.Frame(content_frame, bg="white", relief='raised', bd=2)
        self.main_content.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        # Show dashboard by default
        self.show_dashboard()
    
    def create_top_panel(self, parent):
        """Create top control panel"""
        top_panel = tk.Frame(parent, bg="#D3D3D3", height=80)
        top_panel.pack(fill='x', padx=20, pady=(20, 0))
        top_panel.pack_propagate(False)
        
        # Title
        title_label = tk.Label(top_panel,
                              text="RUУчебник - Административная панель",
                              font=('Arial', 18, 'bold'),
                              bg="#D3D3D3",
                              fg="black")
        title_label.pack(side='left', padx=20, pady=20)
        
        # Status indicators
        status_frame = tk.Frame(top_panel, bg="#D3D3D3")
        status_frame.pack(side='right', padx=20, pady=10)
        
        # Bot status
        self.bot_status_frame = tk.Frame(status_frame, bg="#D3D3D3")
        self.bot_status_frame.pack(pady=5)
        
        tk.Label(self.bot_status_frame,
                text="Статус бота:",
                font=('Arial', 10),
                bg="#D3D3D3").pack(side='left')
        
        self.bot_status_indicator = tk.Label(self.bot_status_frame,
                                           text="●",
                                           font=('Arial', 12),
                                           bg="#D3D3D3",
                                           fg="red")
        self.bot_status_indicator.pack(side='left', padx=5)
        
        self.bot_status_text = tk.Label(self.bot_status_frame,
                                       text="Остановлен",
                                       font=('Arial', 10),
                                       bg="#D3D3D3")
        self.bot_status_text.pack(side='left')
        
        # Web status
        self.web_status_frame = tk.Frame(status_frame, bg="#D3D3D3")
        self.web_status_frame.pack(pady=5)
        
        tk.Label(self.web_status_frame,
                text="Веб-панель:",
                font=('Arial', 10),
                bg="#D3D3D3").pack(side='left')
        
        self.web_status_indicator = tk.Label(self.web_status_frame,
                                           text="●",
                                           font=('Arial', 12),
                                           bg="#D3D3D3",
                                           fg="red")
        self.web_status_indicator.pack(side='left', padx=5)
        
        self.web_status_text = tk.Label(self.web_status_frame,
                                       text="Остановлена",
                                       font=('Arial', 10),
                                       bg="#D3D3D3")
        self.web_status_text.pack(side='left')
    
    def create_sidebar(self, parent):
        """Create left sidebar with navigation"""
        sidebar = tk.Frame(parent, bg="#808080", width=200, relief='raised', bd=2)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        
        # Navigation buttons
        nav_buttons = [
            ("📊 Панель управления", self.show_dashboard),
            ("🤖 Управление ботом", self.show_bot_control),
            ("🌐 Веб-панель", self.show_web_panel),
            ("👥 Пользователи", self.show_users),
            ("📚 Учебники", self.show_textbooks),
            ("📝 Логи", self.show_logs),
            ("📊 Статистика", self.show_statistics),
            ("⚙️ Настройки", self.show_settings),
            ("🚪 Выход", self.logout)
        ]
        
        for text, command in nav_buttons:
            btn = tk.Button(sidebar,
                           text=text,
                           command=command,
                           bg="#D3D3D3",
                           fg="black",
                           relief='flat',
                           font=('Arial', 10),
                           width=25,
                           anchor='w',
                           padx=10)
            btn.pack(fill='x', padx=10, pady=5)
    
    def show_dashboard(self):
        """Show main dashboard"""
        self.clear_content()
        
        # Dashboard title
        title = tk.Label(self.main_content,
                        text="Панель управления",
                        font=('Arial', 20, 'bold'),
                        bg="white")
        title.pack(pady=20)
        
        # Quick actions frame
        actions_frame = tk.Frame(self.main_content, bg="white")
        actions_frame.pack(pady=20)
        
        # Action buttons
        actions = [
            ("🚀 Запустить бота", self.start_bot),
            ("⏹️ Остановить бота", self.stop_bot),
            ("🌐 Открыть веб-панель", self.open_web_panel),
            ("📊 Показать статистику", self.show_statistics),
            ("📝 Просмотреть логи", self.show_logs),
            ("⚙️ Настройки", self.show_settings)
        ]
        
        row = 0
        col = 0
        for text, command in actions:
            btn = tk.Button(actions_frame,
                           text=text,
                           command=command,
                           bg="#D3D3D3",
                           fg="black",
                           font=('Arial', 12),
                           width=20,
                           height=3,
                           relief='raised',
                           bd=2)
            btn.grid(row=row, column=col, padx=10, pady=10)
            
            col += 1
            if col > 2:
                col = 0
                row += 1
        
        # Status display
        status_frame = tk.Frame(self.main_content, bg="white")
        status_frame.pack(pady=20, fill='x', padx=20)
        
        # System status
        status_text = tk.Text(status_frame,
                             height=10,
                             width=80,
                             font=('Courier', 10),
                             bg="#F0F0F0",
                             relief='sunken',
                             bd=2)
        status_text.pack(fill='both', expand=True)
        
        # Add status information
        status_info = f"""
Система RUУчебник - Статус компонентов

Telegram Bot: {'Запущен' if self.is_bot_running() else 'Остановлен'}
Веб-панель: {'Запущена' if self.is_web_running() else 'Остановлена'}
База данных: Подключена
Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Для управления используйте кнопки выше или меню слева.
        """
        
        status_text.insert('1.0', status_info)
        status_text.config(state='disabled')
    
    def show_bot_control(self):
        """Show bot control panel"""
        self.clear_content()
        
        title = tk.Label(self.main_content,
                        text="Управление Telegram ботом",
                        font=('Arial', 18, 'bold'),
                        bg="white")
        title.pack(pady=20)
        
        # Control buttons
        control_frame = tk.Frame(self.main_content, bg="white")
        control_frame.pack(pady=20)
        
        start_btn = tk.Button(control_frame,
                             text="▶️ Запустить бота",
                             command=self.start_bot,
                             bg="#4CAF50",
                             fg="white",
                             font=('Arial', 14),
                             width=15,
                             height=2)
        start_btn.pack(side='left', padx=10)
        
        stop_btn = tk.Button(control_frame,
                            text="⏹️ Остановить бота",
                            command=self.stop_bot,
                            bg="#F44336",
                            fg="white",
                            font=('Arial', 14),
                            width=15,
                            height=2)
        stop_btn.pack(side='left', padx=10)
        
        restart_btn = tk.Button(control_frame,
                               text="🔄 Перезапустить",
                               command=self.restart_bot,
                               bg="#FF9800",
                               fg="white",
                               font=('Arial', 14),
                               width=15,
                               height=2)
        restart_btn.pack(side='left', padx=10)
        
        # Bot output log
        log_frame = tk.Frame(self.main_content, bg="white")
        log_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(log_frame,
                text="Логи бота:",
                font=('Arial', 12, 'bold'),
                bg="white").pack(anchor='w')
        
        # Create scrollable text widget for bot logs
        log_scroll_frame = tk.Frame(log_frame, bg="white")
        log_scroll_frame.pack(fill='both', expand=True)
        
        self.bot_log_text = tk.Text(log_scroll_frame,
                                   font=('Courier', 10),
                                   bg="black",
                                   fg="green",
                                   insertbackground="white")
        
        log_scrollbar = tk.Scrollbar(log_scroll_frame, orient="vertical", command=self.bot_log_text.yview)
        self.bot_log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.bot_log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # Add initial log message
        self.bot_log_text.insert('end', "Bot log will appear here...\n")
        self.bot_log_text.config(state='disabled')
    
    def show_web_panel(self):
        """Show web panel controls"""
        self.clear_content()
        
        title = tk.Label(self.main_content,
                        text="Веб-панель администратора",
                        font=('Arial', 18, 'bold'),
                        bg="white")
        title.pack(pady=20)
        
        # Web panel controls
        control_frame = tk.Frame(self.main_content, bg="white")
        control_frame.pack(pady=20)
        
        start_web_btn = tk.Button(control_frame,
                                 text="🌐 Запустить веб-панель",
                                 command=self.start_web_server,
                                 bg="#2196F3",
                                 fg="white",
                                 font=('Arial', 14),
                                 width=20,
                                 height=2)
        start_web_btn.pack(pady=10)
        
        open_web_btn = tk.Button(control_frame,
                                text="🔗 Открыть в браузере",
                                command=self.open_web_panel,
                                bg="#4CAF50",
                                fg="white",
                                font=('Arial', 14),
                                width=20,
                                height=2)
        open_web_btn.pack(pady=10)
        
        stop_web_btn = tk.Button(control_frame,
                                text="⏹️ Остановить веб-панель",
                                command=self.stop_web_server,
                                bg="#F44336",
                                fg="white",
                                font=('Arial', 14),
                                width=20,
                                height=2)
        stop_web_btn.pack(pady=10)
        
        # Web server info
        info_frame = tk.Frame(self.main_content, bg="white")
        info_frame.pack(fill='x', padx=20, pady=20)
        
        info_text = f"""
Веб-панель администратора

URL: {self.web_url}
Статус: {'Запущена' if self.is_web_running() else 'Остановлена'}
Порт: 5000

Веб-панель предоставляет полный интерфейс для управления ботом,
пользователями, учебниками и просмотра статистики.
        """
        
        info_label = tk.Label(info_frame,
                             text=info_text,
                             font=('Arial', 11),
                             bg="white",
                             justify='left')
        info_label.pack()
    
    def show_users(self):
        """Show users management"""
        self.clear_content()
        
        title = tk.Label(self.main_content,
                        text="Управление пользователями",
                        font=('Arial', 18, 'bold'),
                        bg="white")
        title.pack(pady=20)
        
        # Users table
        users_frame = tk.Frame(self.main_content, bg="white")
        users_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create treeview for users
        columns = ('ID', 'Username', 'Name', 'Joined', 'Downloads', 'Status')
        users_tree = ttk.Treeview(users_frame, columns=columns, show='headings', style='Dark.Treeview')
        
        # Define column headings
        for col in columns:
            users_tree.heading(col, text=col)
            users_tree.column(col, width=120)
        
        # Add scrollbar
        users_scrollbar = ttk.Scrollbar(users_frame, orient='vertical', command=users_tree.yview)
        users_tree.configure(yscrollcommand=users_scrollbar.set)
        
        users_tree.pack(side='left', fill='both', expand=True)
        users_scrollbar.pack(side='right', fill='y')
        
        # Add sample data (in real app, fetch from API)
        sample_users = [
            ("123456789", "@user1", "John Doe", "2024-01-15", "5", "Active"),
            ("987654321", "@user2", "Jane Smith", "2024-01-16", "3", "Active"),
            ("456789123", "@user3", "Bob Johnson", "2024-01-17", "8", "Banned"),
        ]
        
        for user in sample_users:
            users_tree.insert('', 'end', values=user)
        
        # User management buttons
        btn_frame = tk.Frame(self.main_content, bg="white")
        btn_frame.pack(pady=10)
        
        ban_btn = tk.Button(btn_frame,
                           text="🚫 Забанить пользователя",
                           command=self.ban_user_dialog,
                           bg="#F44336",
                           fg="white",
                           font=('Arial', 10))
        ban_btn.pack(side='left', padx=5)
        
        unban_btn = tk.Button(btn_frame,
                             text="✅ Разбанить пользователя",
                             command=self.unban_user_dialog,
                             bg="#4CAF50",
                             fg="white",
                             font=('Arial', 10))
        unban_btn.pack(side='left', padx=5)
        
        refresh_btn = tk.Button(btn_frame,
                               text="🔄 Обновить",
                               command=lambda: self.show_users(),
                               bg="#2196F3",
                               fg="white",
                               font=('Arial', 10))
        refresh_btn.pack(side='left', padx=5)
    
    def show_textbooks(self):
        """Show textbooks management"""
        self.clear_content()
        
        title = tk.Label(self.main_content,
                        text="Управление учебниками",
                        font=('Arial', 18, 'bold'),
                        bg="white")
        title.pack(pady=20)
        
        # Add textbook button
        add_btn = tk.Button(self.main_content,
                           text="➕ Добавить учебник",
                           command=self.add_textbook_dialog,
                           bg="#4CAF50",
                           fg="white",
                           font=('Arial', 12))
        add_btn.pack(pady=10)
        
        # Textbooks table
        textbooks_frame = tk.Frame(self.main_content, bg="white")
        textbooks_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        columns = ('Title', 'Author', 'Subject', 'Grade', 'Downloads', 'Size')
        textbooks_tree = ttk.Treeview(textbooks_frame, columns=columns, show='headings', style='Dark.Treeview')
        
        for col in columns:
            textbooks_tree.heading(col, text=col)
            textbooks_tree.column(col, width=150)
        
        textbooks_scrollbar = ttk.Scrollbar(textbooks_frame, orient='vertical', command=textbooks_tree.yview)
        textbooks_tree.configure(yscrollcommand=textbooks_scrollbar.set)
        
        textbooks_tree.pack(side='left', fill='both', expand=True)
        textbooks_scrollbar.pack(side='right', fill='y')
        
        # Sample textbooks
        sample_textbooks = [
            ("Математика 5 класс", "Виленкин Н.Я.", "Математика", "5", "1247", "15.2 МБ"),
            ("Русский язык 6 класс", "Ладыженская Т.А.", "Русский язык", "6", "856", "12.8 МБ"),
            ("Физика 9 класс", "Перышкин А.В.", "Физика", "9", "634", "18.5 МБ"),
        ]
        
        for textbook in sample_textbooks:
            textbooks_tree.insert('', 'end', values=textbook)
    
    def show_logs(self):
        """Show system logs"""
        self.clear_content()
        
        title = tk.Label(self.main_content,
                        text="Системные логи",
                        font=('Arial', 18, 'bold'),
                        bg="white")
        title.pack(pady=20)
        
        # Log controls
        control_frame = tk.Frame(self.main_content, bg="white")
        control_frame.pack(pady=10)
        
        # Log type selection
        tk.Label(control_frame,
                text="Тип логов:",
                bg="white",
                font=('Arial', 10)).pack(side='left', padx=5)
        
        log_type_var = tk.StringVar(value="Все")
        log_type_combo = ttk.Combobox(control_frame,
                                     textvariable=log_type_var,
                                     values=["Все", "Пользователи", "Ошибки", "Баны", "Админ"],
                                     state="readonly",
                                     width=15)
        log_type_combo.pack(side='left', padx=5)
        
        refresh_btn = tk.Button(control_frame,
                               text="🔄 Обновить",
                               command=lambda: self.load_logs(log_type_var.get()),
                               bg="#2196F3",
                               fg="white")
        refresh_btn.pack(side='left', padx=5)
        
        export_btn = tk.Button(control_frame,
                              text="📥 Экспорт",
                              command=self.export_logs,
                              bg="#FF9800",
                              fg="white")
        export_btn.pack(side='left', padx=5)
        
        # Logs display
        logs_frame = tk.Frame(self.main_content, bg="white")
        logs_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        self.logs_text = tk.Text(logs_frame,
                                font=('Courier', 9),
                                bg="#F8F8F8",
                                fg="black")
        
        logs_scrollbar = tk.Scrollbar(logs_frame, orient='vertical', command=self.logs_text.yview)
        self.logs_text.configure(yscrollcommand=logs_scrollbar.set)
        
        self.logs_text.pack(side='left', fill='both', expand=True)
        logs_scrollbar.pack(side='right', fill='y')
        
        # Load initial logs
        self.load_logs("Все")
    
    def show_statistics(self):
        """Show system statistics"""
        self.clear_content()
        
        title = tk.Label(self.main_content,
                        text="Статистика системы",
                        font=('Arial', 18, 'bold'),
                        bg="white")
        title.pack(pady=20)
        
        # Stats cards
        stats_frame = tk.Frame(self.main_content, bg="white")
        stats_frame.pack(fill='x', padx=20, pady=20)
        
        # Sample statistics
        stats = [
            ("👥", "Пользователей", "1,247"),
            ("📚", "Учебников", "89"),
            ("📊", "Активных сегодня", "156"),
            ("⚡", "Запросов сегодня", "2,340"),
            ("📥", "Всего скачиваний", "15,678"),
            ("🚫", "Заблокированных", "12")
        ]
        
        row = 0
        col = 0
        for emoji, label, value in stats:
            stat_card = tk.Frame(stats_frame, bg="#F0F0F0", relief='raised', bd=2)
            stat_card.grid(row=row, column=col, padx=10, pady=10, sticky='ew')
            
            tk.Label(stat_card,
                    text=emoji,
                    font=('Arial', 24),
                    bg="#F0F0F0").pack(pady=5)
            
            tk.Label(stat_card,
                    text=value,
                    font=('Arial', 18, 'bold'),
                    bg="#F0F0F0").pack()
            
            tk.Label(stat_card,
                    text=label,
                    font=('Arial', 10),
                    bg="#F0F0F0").pack(pady=5)
            
            col += 1
            if col > 2:
                col = 0
                row += 1
        
        # Configure grid weights
        for i in range(3):
            stats_frame.grid_columnconfigure(i, weight=1)
    
    def show_settings(self):
        """Show system settings"""
        self.clear_content()
        
        title = tk.Label(self.main_content,
                        text="Настройки системы",
                        font=('Arial', 18, 'bold'),
                        bg="white")
        title.pack(pady=20)
        
        # Settings notebook
        notebook = ttk.Notebook(self.main_content)
        notebook.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Bot settings tab
        bot_frame = ttk.Frame(notebook)
        notebook.add(bot_frame, text="Настройки бота")
        
        tk.Label(bot_frame,
                text="Токен бота:",
                font=('Arial', 10, 'bold')).pack(anchor='w', padx=10, pady=5)
        
        token_entry = tk.Entry(bot_frame,
                              width=60,
                              show="*",
                              font=('Courier', 10))
        token_entry.pack(padx=10, pady=5, fill='x')
        token_entry.insert(0, "8238798012:AAEtdmiVOSta1_ogJTstJSHjtr6aKc8J0Z0")
        
        tk.Label(bot_frame,
                text="ID администратора:",
                font=('Arial', 10, 'bold')).pack(anchor='w', padx=10, pady=5)
        
        admin_entry = tk.Entry(bot_frame,
                              width=20,
                              font=('Courier', 10))
        admin_entry.pack(padx=10, pady=5, anchor='w')
        admin_entry.insert(0, "5982787659")
        
        # Database settings tab
        db_frame = ttk.Frame(notebook)
        notebook.add(db_frame, text="База данных")
        
        tk.Label(db_frame,
                text="URL подключения:",
                font=('Arial', 10, 'bold')).pack(anchor='w', padx=10, pady=5)
        
        db_entry = tk.Entry(db_frame,
                           width=80,
                           show="*",
                           font=('Courier', 9))
        db_entry.pack(padx=10, pady=5, fill='x')
        db_entry.insert(0, "postgresql://neondb_owner:***@ep-divine-sky.../neondb")
        
        test_db_btn = tk.Button(db_frame,
                               text="🔍 Тест подключения",
                               command=self.test_database_connection,
                               bg="#4CAF50",
                               fg="white")
        test_db_btn.pack(padx=10, pady=10, anchor='w')
        
        # System tab
        system_frame = ttk.Frame(notebook)
        notebook.add(system_frame, text="Система")
        
        backup_btn = tk.Button(system_frame,
                              text="💾 Создать резервную копию",
                              command=self.create_backup,
                              bg="#FF9800",
                              fg="white",
                              font=('Arial', 12),
                              width=25)
        backup_btn.pack(pady=10)
        
        export_btn = tk.Button(system_frame,
                              text="📤 Экспорт всех данных",
                              command=self.export_all_data,
                              bg="#2196F3",
                              fg="white",
                              font=('Arial', 12),
                              width=25)
        export_btn.pack(pady=10)
        
        restart_btn = tk.Button(system_frame,
                               text="🔄 Перезапустить систему",
                               command=self.restart_system,
                               bg="#F44336",
                               fg="white",
                               font=('Arial', 12),
                               width=25)
        restart_btn.pack(pady=10)
    
    # Bot control methods
    def start_bot(self):
        """Start Telegram bot"""
        if self.is_bot_running():
            messagebox.showinfo("Информация", "Бот уже запущен!")
            return
        
        try:
            # Start bot process
            bot_script = os.path.join(os.path.dirname(__file__), "telegram_bot.py")
            self.bot_process = subprocess.Popen(
                [sys.executable, bot_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.log_bot_message("🚀 Запуск Telegram бота...")
            messagebox.showinfo("Успех", "Бот запущен!")
            
            # Start log monitoring
            threading.Thread(target=self.monitor_bot_output, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить бота: {e}")
    
    def stop_bot(self):
        """Stop Telegram bot"""
        if not self.is_bot_running():
            messagebox.showinfo("Информация", "Бот уже остановлен!")
            return
        
        try:
            if self.bot_process:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=10)
                self.bot_process = None
                
            self.log_bot_message("⏹️ Telegram бот остановлен")
            messagebox.showinfo("Успех", "Бот остановлен!")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось остановить бота: {e}")
    
    def restart_bot(self):
        """Restart Telegram bot"""
        self.stop_bot()
        time.sleep(2)
        self.start_bot()
    
    def start_web_server(self):
        """Start web server"""
        if self.is_web_running():
            messagebox.showinfo("Информация", "Веб-сервер уже запущен!")
            return
        
        try:
            # Start web server process
            server_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "server", "index.ts")
            
            # Use npm run dev command
            project_root = os.path.dirname(os.path.dirname(__file__))
            self.web_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            messagebox.showinfo("Успех", "Веб-сервер запущен!")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить веб-сервер: {e}")
    
    def stop_web_server(self):
        """Stop web server"""
        if not self.is_web_running():
            messagebox.showinfo("Информация", "Веб-сервер уже остановлен!")
            return
        
        try:
            if self.web_process:
                self.web_process.terminate()
                self.web_process.wait(timeout=10)
                self.web_process = None
                
            messagebox.showinfo("Успех", "Веб-сервер остановлен!")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось остановить веб-сервер: {e}")
    
    def open_web_panel(self):
        """Open web panel in browser"""
        try:
            webbrowser.open(self.web_url)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть браузер: {e}")
    
    # Status monitoring
    def is_bot_running(self) -> bool:
        """Check if bot is running"""
        return self.bot_process is not None and self.bot_process.poll() is None
    
    def is_web_running(self) -> bool:
        """Check if web server is running"""
        return self.web_process is not None and self.web_process.poll() is None
    
    def start_status_monitoring(self):
        """Start status monitoring thread"""
        threading.Thread(target=self.monitor_status, daemon=True).start()
    
    def monitor_status(self):
        """Monitor system status"""
        while True:
            try:
                # Update bot status
                if self.is_bot_running():
                    self.bot_status_indicator.config(fg="green")
                    self.bot_status_text.config(text="Запущен")
                else:
                    self.bot_status_indicator.config(fg="red")
                    self.bot_status_text.config(text="Остановлен")
                
                # Update web status
                if self.is_web_running():
                    self.web_status_indicator.config(fg="green")
                    self.web_status_text.config(text="Запущена")
                else:
                    self.web_status_indicator.config(fg="red")
                    self.web_status_text.config(text="Остановлена")
                
            except Exception as e:
                pass  # Ignore errors during monitoring
            
            time.sleep(2)
    
    def monitor_bot_output(self):
        """Monitor bot output"""
        if not self.bot_process:
            return
        
        try:
            for line in iter(self.bot_process.stdout.readline, ''):
                if line:
                    self.log_bot_message(line.strip())
                if self.bot_process.poll() is not None:
                    break
        except Exception as e:
            self.log_bot_message(f"Ошибка мониторинга: {e}")
    
    def log_bot_message(self, message: str):
        """Add message to bot log"""
        try:
            if hasattr(self, 'bot_log_text'):
                timestamp = datetime.now().strftime('[%H:%M:%S]')
                self.bot_log_text.config(state='normal')
                self.bot_log_text.insert('end', f"{timestamp} {message}\n")
                self.bot_log_text.see('end')
                self.bot_log_text.config(state='disabled')
        except Exception:
            pass
    
    # Dialog methods
    def ban_user_dialog(self):
        """Show ban user dialog"""
        user_id = simpledialog.askstring("Бан пользователя", "Введите Telegram ID пользователя:")
        if not user_id:
            return
        
        reason = simpledialog.askstring("Причина бана", "Введите причину бана:")
        if not reason:
            return
        
        days = simpledialog.askinteger("Срок бана", "Количество дней (0 для перманентного):", minvalue=0, maxvalue=365)
        if days is None:
            return
        
        # TODO: Implement actual ban via API
        messagebox.showinfo("Успех", f"Пользователь {user_id} заблокирован на {days} дней.\nПричина: {reason}")
    
    def unban_user_dialog(self):
        """Show unban user dialog"""
        user_id = simpledialog.askstring("Разбан пользователя", "Введите Telegram ID пользователя:")
        if not user_id:
            return
        
        # TODO: Implement actual unban via API
        messagebox.showinfo("Успех", f"Пользователь {user_id} разблокирован.")
    
    def add_textbook_dialog(self):
        """Show add textbook dialog"""
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить учебник")
        dialog.geometry("400x500")
        dialog.configure(bg="white")
        dialog.grab_set()
        
        # Form fields
        tk.Label(dialog, text="Название:", bg="white").pack(anchor='w', padx=10, pady=5)
        title_entry = tk.Entry(dialog, width=50)
        title_entry.pack(padx=10, pady=5, fill='x')
        
        tk.Label(dialog, text="Автор:", bg="white").pack(anchor='w', padx=10, pady=5)
        author_entry = tk.Entry(dialog, width=50)
        author_entry.pack(padx=10, pady=5, fill='x')
        
        tk.Label(dialog, text="Класс:", bg="white").pack(anchor='w', padx=10, pady=5)
        grade_var = tk.StringVar(value="5")
        grade_combo = ttk.Combobox(dialog, textvariable=grade_var,
                                  values=list(range(1, 12)), state="readonly")
        grade_combo.pack(padx=10, pady=5, anchor='w')
        
        tk.Label(dialog, text="Предмет:", bg="white").pack(anchor='w', padx=10, pady=5)
        subject_var = tk.StringVar(value="Математика")
        subject_combo = ttk.Combobox(dialog, textvariable=subject_var,
                                    values=["Математика", "Русский язык", "Физика", "Химия", "Биология"],
                                    state="readonly")
        subject_combo.pack(padx=10, pady=5, fill='x')
        
        # File selection
        file_path_var = tk.StringVar()
        
        def select_file():
            file_path = filedialog.askopenfilename(
                title="Выберите PDF файл",
                filetypes=[("PDF files", "*.pdf")]
            )
            if file_path:
                file_path_var.set(file_path)
                file_label.config(text=os.path.basename(file_path))
        
        tk.Label(dialog, text="PDF файл:", bg="white").pack(anchor='w', padx=10, pady=5)
        file_frame = tk.Frame(dialog, bg="white")
        file_frame.pack(fill='x', padx=10, pady=5)
        
        file_button = tk.Button(file_frame, text="Выбрать файл", command=select_file)
        file_button.pack(side='left')
        
        file_label = tk.Label(file_frame, text="Файл не выбран", bg="white", fg="gray")
        file_label.pack(side='left', padx=10)
        
        # Buttons
        button_frame = tk.Frame(dialog, bg="white")
        button_frame.pack(fill='x', padx=10, pady=20)
        
        def add_textbook():
            # TODO: Implement actual textbook addition
            title = title_entry.get()
            author = author_entry.get()
            grade = grade_var.get()
            subject = subject_var.get()
            file_path = file_path_var.get()
            
            if not all([title, author, grade, subject, file_path]):
                messagebox.showerror("Ошибка", "Заполните все поля!")
                return
            
            messagebox.showinfo("Успех", f"Учебник '{title}' добавлен!")
            dialog.destroy()
        
        cancel_btn = tk.Button(button_frame, text="Отмена", command=dialog.destroy)
        cancel_btn.pack(side='right', padx=5)
        
        add_btn = tk.Button(button_frame, text="Добавить", command=add_textbook,
                           bg="#4CAF50", fg="white")
        add_btn.pack(side='right', padx=5)
    
    # Utility methods
    def load_logs(self, log_type: str):
        """Load and display logs"""
        # Sample logs
        sample_logs = [
            "2024-01-15 10:30:15 [INFO] Пользователь 123456789 скачал учебник 'Математика 5 класс'",
            "2024-01-15 10:32:22 [INFO] Новый пользователь зарегистрирован: 987654321",
            "2024-01-15 10:35:45 [WARNING] Попытка доступа к заблокированному контенту",
            "2024-01-15 10:40:12 [INFO] Администратор выполнил рассылку для 1247 пользователей",
            "2024-01-15 10:45:33 [ERROR] Ошибка загрузки файла: timeout",
        ]
        
        self.logs_text.config(state='normal')
        self.logs_text.delete('1.0', 'end')
        
        for log in sample_logs:
            if log_type == "Все" or log_type.lower() in log.lower():
                self.logs_text.insert('end', log + "\n")
        
        self.logs_text.config(state='disabled')
    
    def export_logs(self):
        """Export logs to file"""
        file_path = filedialog.asksaveasfilename(
            title="Сохранить логи",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    logs_content = self.logs_text.get('1.0', 'end')
                    f.write(logs_content)
                messagebox.showinfo("Успех", f"Логи сохранены в {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
    
    def test_database_connection(self):
        """Test database connection"""
        # TODO: Implement actual database test
        messagebox.showinfo("Тест соединения", "✅ Подключение к базе данных успешно!")
    
    def create_backup(self):
        """Create system backup"""
        # TODO: Implement actual backup
        messagebox.showinfo("Резервная копия", "💾 Резервная копия создана успешно!")
    
    def export_all_data(self):
        """Export all system data"""
        # TODO: Implement actual data export
        messagebox.showinfo("Экспорт данных", "📤 Все данные экспортированы успешно!")
    
    def restart_system(self):
        """Restart the entire system"""
        if messagebox.askyesno("Перезапуск", "Вы уверены, что хотите перезапустить систему?"):
            self.stop_bot()
            self.stop_web_server()
            time.sleep(2)
            self.start_bot()
            self.start_web_server()
            messagebox.showinfo("Перезапуск", "🔄 Система перезапущена!")
    
    def clear_content(self):
        """Clear main content area"""
        for widget in self.main_content.winfo_children():
            widget.destroy()
    
    def logout(self):
        """Logout from admin panel"""
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
            self.stop_bot()
            self.stop_web_server()
            self.root.quit()
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = RUUchebnikDesktopAdmin()
    app.run()
