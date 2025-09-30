#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенное десктопное приложение RUУчебник с управлением изображениями
Включает функции для замены изображений, управления ботом и веб-интерфейсом
"""

import sys
import os
import json
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
from typing import Optional, Dict, List
import requests
from PIL import Image, ImageTk
import webbrowser

class RUUchebnikDesktopApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RUУчебник - Административная панель")
        self.root.geometry("1400x900")
        self.root.configure(bg="#001F3F")
        
        # Configuration
        self.bot_process: Optional[subprocess.Popen] = None
        self.web_process: Optional[subprocess.Popen] = None
        self.is_authenticated = False
        
        # Paths for images
        self.images_dir = "images"
        self.create_images_directory()
        
        # Image management
        self.current_images = {
            "rules": None,
            "solver": None,
            "textbooks": None,
            "help_author": None
        }
        
        self.setup_styles()
        self.create_main_interface()
        self.load_existing_images()
        
    def create_images_directory(self):
        """Создание директории для изображений"""
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
        
        # Создаем поддиректории для каждого типа изображений
        subdirs = ["rules", "solver", "textbooks", "help"]
        for subdir in subdirs:
            path = os.path.join(self.images_dir, subdir)
            if not os.path.exists(path):
                os.makedirs(path)
    
    def setup_styles(self):
        """Настройка стилей интерфейса"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Стили для кнопок
        style.configure('Dark.TButton',
                       background='#4CAF50',
                       foreground='white',
                       borderwidth=2,
                       focuscolor='none',
                       relief='raised')
        style.map('Dark.TButton',
                 background=[('active', '#45a049')])
        
        # Стили для фреймов
        style.configure('Dark.TFrame',
                       background='#2C3E50',
                       relief='raised',
                       borderwidth=2)
        
        # Стили для меток
        style.configure('Dark.TLabel',
                       background='#2C3E50',
                       foreground='white',
                       font=('Arial', 12))
        
        style.configure('Title.TLabel',
                       background='#001F3F',
                       foreground='white',
                       font=('Arial', 20, 'bold'))
    
    def create_main_interface(self):
        """Создание основного интерфейса"""
        # Заголовок
        title_frame = ttk.Frame(self.root, style='Dark.TFrame')
        title_frame.pack(fill='x', padx=10, pady=5)
        
        title_label = ttk.Label(title_frame, 
                               text="🎓 RUУчебник - Административная панель", 
                               style='Title.TLabel')
        title_label.pack(pady=10)
        
        # Создание вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Вкладка управления ботом
        self.create_bot_management_tab()
        
        # Вкладка управления изображениями
        self.create_image_management_tab()
        
        # Вкладка админ-панели
        self.create_admin_panel_tab()
        
        # Вкладка веб-интерфейса
        self.create_web_interface_tab()
    
    def create_bot_management_tab(self):
        """Создание вкладки управления ботом"""
        bot_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(bot_frame, text="🤖 Управление ботом")
        
        # Статус бота
        status_frame = ttk.LabelFrame(bot_frame, text="Статус бота", style='Dark.TFrame')
        status_frame.pack(fill='x', padx=10, pady=5)
        
        self.bot_status_label = ttk.Label(status_frame, 
                                         text="❌ Бот остановлен", 
                                         style='Dark.TLabel')
        self.bot_status_label.pack(pady=5)
        
        # Кнопки управления
        control_frame = ttk.Frame(status_frame, style='Dark.TFrame')
        control_frame.pack(pady=10)
        
        self.start_bot_btn = ttk.Button(control_frame, 
                                       text="🚀 Запустить бота", 
                                       command=self.start_bot,
                                       style='Dark.TButton')
        self.start_bot_btn.pack(side='left', padx=5)
        
        self.stop_bot_btn = ttk.Button(control_frame, 
                                      text="⏹️ Остановить бота", 
                                      command=self.stop_bot,
                                      style='Dark.TButton')
        self.stop_bot_btn.pack(side='left', padx=5)
        
        self.restart_bot_btn = ttk.Button(control_frame, 
                                         text="🔄 Перезапустить бота", 
                                         command=self.restart_bot,
                                         style='Dark.TButton')
        self.restart_bot_btn.pack(side='left', padx=5)
        
        # Логи бота
        logs_frame = ttk.LabelFrame(bot_frame, text="Логи бота", style='Dark.TFrame')
        logs_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(logs_frame, 
                               bg='#1e1e1e', 
                               fg='white', 
                               wrap='word',
                               font=('Courier', 10))
        log_scrollbar = ttk.Scrollbar(logs_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
    
    def create_image_management_tab(self):
        """Создание вкладки управления изображениями"""
        img_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(img_frame, text="🖼️ Управление изображениями")
        
        # Создаем Canvas для прокрутки
        canvas = tk.Canvas(img_frame, bg='#2C3E50')
        scrollbar = ttk.Scrollbar(img_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Dark.TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Управление изображениями для разных функций
        self.create_image_section(scrollable_frame, "rules", "🔒 Изображение правил")
        self.create_image_section(scrollable_frame, "solver", "🧮 Изображение решатора")  
        self.create_image_section(scrollable_frame, "textbooks", "📚 Изображение учебников")
        self.create_image_section(scrollable_frame, "help_author", "❓ Изображение помощи (выбор автора)")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_image_section(self, parent, image_type: str, title: str):
        """Создание секции для управления одним типом изображений"""
        section_frame = ttk.LabelFrame(parent, text=title, style='Dark.TFrame')
        section_frame.pack(fill='x', padx=10, pady=10)
        
        # Отображение текущего изображения
        img_display_frame = ttk.Frame(section_frame, style='Dark.TFrame')
        img_display_frame.pack(pady=10)
        
        # Метка для изображения
        img_label = ttk.Label(img_display_frame, text="Изображение не загружено", style='Dark.TLabel')
        img_label.pack()
        setattr(self, f"{image_type}_img_label", img_label)
        
        # Метка с информацией о файле
        info_label = ttk.Label(img_display_frame, text="", style='Dark.TLabel')
        info_label.pack()
        setattr(self, f"{image_type}_info_label", info_label)
        
        # Кнопки управления
        btn_frame = ttk.Frame(section_frame, style='Dark.TFrame')
        btn_frame.pack(pady=10)
        
        add_btn = ttk.Button(btn_frame, 
                            text="➕ Добавить изображение", 
                            command=lambda: self.add_image(image_type),
                            style='Dark.TButton')
        add_btn.pack(side='left', padx=5)
        
        change_btn = ttk.Button(btn_frame, 
                               text="🔄 Изменить изображение", 
                               command=lambda: self.change_image(image_type),
                               style='Dark.TButton')
        change_btn.pack(side='left', padx=5)
        
        delete_btn = ttk.Button(btn_frame, 
                               text="🗑️ Удалить изображение", 
                               command=lambda: self.delete_image(image_type),
                               style='Dark.TButton')
        delete_btn.pack(side='left', padx=5)
    
    def create_admin_panel_tab(self):
        """Создание вкладки админ-панели"""
        admin_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(admin_frame, text="👑 Админ-панель")
        
        # Управление администраторами
        admin_mgmt_frame = ttk.LabelFrame(admin_frame, text="Управление администраторами", style='Dark.TFrame')
        admin_mgmt_frame.pack(fill='x', padx=10, pady=5)
        
        # Добавление админа
        add_admin_frame = ttk.Frame(admin_mgmt_frame, style='Dark.TFrame')
        add_admin_frame.pack(pady=10)
        
        ttk.Label(add_admin_frame, text="ID нового админа:", style='Dark.TLabel').pack(side='left')
        self.admin_id_entry = ttk.Entry(add_admin_frame)
        self.admin_id_entry.pack(side='left', padx=5)
        
        ttk.Button(add_admin_frame, 
                  text="➕ Добавить админа", 
                  command=self.add_admin,
                  style='Dark.TButton').pack(side='left', padx=5)
        
        # Список админов
        admins_list_frame = ttk.LabelFrame(admin_frame, text="Текущие администраторы", style='Dark.TFrame')
        admins_list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.admins_listbox = tk.Listbox(admins_list_frame, bg='#1e1e1e', fg='white')
        admins_scrollbar = ttk.Scrollbar(admins_list_frame, orient='vertical', command=self.admins_listbox.yview)
        self.admins_listbox.configure(yscrollcommand=admins_scrollbar.set)
        
        self.admins_listbox.pack(side='left', fill='both', expand=True)
        admins_scrollbar.pack(side='right', fill='y')
        
        # Кнопка удаления админа
        ttk.Button(admins_list_frame, 
                  text="🗑️ Удалить выбранного админа", 
                  command=self.remove_admin,
                  style='Dark.TButton').pack(pady=5)
    
    def create_web_interface_tab(self):
        """Создание вкладки веб-интерфейса"""
        web_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(web_frame, text="🌐 Веб-интерфейс")
        
        # Статус веб-сервера
        web_status_frame = ttk.LabelFrame(web_frame, text="Статус веб-сервера", style='Dark.TFrame')
        web_status_frame.pack(fill='x', padx=10, pady=5)
        
        self.web_status_label = ttk.Label(web_status_frame, 
                                         text="❌ Веб-сервер остановлен", 
                                         style='Dark.TLabel')
        self.web_status_label.pack(pady=5)
        
        # Кнопки управления веб-сервером
        web_control_frame = ttk.Frame(web_status_frame, style='Dark.TFrame')
        web_control_frame.pack(pady=10)
        
        ttk.Button(web_control_frame, 
                  text="🚀 Запустить веб-сервер", 
                  command=self.start_web_server,
                  style='Dark.TButton').pack(side='left', padx=5)
        
        ttk.Button(web_control_frame, 
                  text="⏹️ Остановить веб-сервер", 
                  command=self.stop_web_server,
                  style='Dark.TButton').pack(side='left', padx=5)
        
        ttk.Button(web_control_frame, 
                  text="🌐 Открыть в браузере", 
                  command=self.open_web_interface,
                  style='Dark.TButton').pack(side='left', padx=5)
        
        # Настройки веб-интерфейса
        web_settings_frame = ttk.LabelFrame(web_frame, text="Настройки веб-интерфейса", style='Dark.TFrame')
        web_settings_frame.pack(fill='x', padx=10, pady=5)
        
        # Порт
        port_frame = ttk.Frame(web_settings_frame, style='Dark.TFrame')
        port_frame.pack(pady=5)
        
        ttk.Label(port_frame, text="Порт:", style='Dark.TLabel').pack(side='left')
        self.port_entry = ttk.Entry(port_frame)
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(side='left', padx=5)
    
    def load_existing_images(self):
        """Загрузка существующих изображений"""
        for image_type in self.current_images.keys():
            self.load_image_for_type(image_type)
    
    def load_image_for_type(self, image_type: str):
        """Загрузка изображения для конкретного типа"""
        image_dir = os.path.join(self.images_dir, image_type.replace("_", "/"))
        if os.path.exists(image_dir):
            # Ищем первое изображение в директории
            for file in os.listdir(image_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    image_path = os.path.join(image_dir, file)
                    self.display_image(image_type, image_path)
                    break
    
    def display_image(self, image_type: str, image_path: str):
        """Отображение изображения в интерфейсе"""
        try:
            # Загружаем и изменяем размер изображения
            img = Image.open(image_path)
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Получаем метку для отображения
            img_label = getattr(self, f"{image_type}_img_label")
            img_label.configure(image=photo, text="")
            img_label.image = photo  # Сохраняем ссылку
            
            # Обновляем информацию о файле
            info_label = getattr(self, f"{image_type}_info_label")
            file_size = os.path.getsize(image_path)
            info_text = f"Файл: {os.path.basename(image_path)}\nРазмер: {file_size} байт"
            info_label.configure(text=info_text)
            
            # Сохраняем путь к изображению
            self.current_images[image_type] = image_path
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить изображение: {e}")
    
    def add_image(self, image_type: str):
        """Добавление нового изображения"""
        file_path = filedialog.askopenfilename(
            title=f"Выберите изображение для {image_type}",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        
        if file_path:
            # Копируем файл в нужную директорию
            target_dir = os.path.join(self.images_dir, image_type.replace("_", "/"))
            target_path = os.path.join(target_dir, os.path.basename(file_path))
            
            try:
                import shutil
                shutil.copy2(file_path, target_path)
                self.display_image(image_type, target_path)
                messagebox.showinfo("Успех", "Изображение добавлено успешно!")
                
                # Запрашиваем название/описание изображения
                description = simpledialog.askstring(
                    "Описание изображения",
                    f"Введите описание для изображения {image_type}:",
                    initialvalue=f"Изображение для {image_type}"
                )
                
                if description:
                    self.save_image_metadata(image_type, target_path, description)
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось добавить изображение: {e}")
    
    def change_image(self, image_type: str):
        """Изменение существующего изображения"""
        if not self.current_images.get(image_type):
            messagebox.showwarning("Предупреждение", "Сначала добавьте изображение")
            return
        
        self.add_image(image_type)  # Используем ту же логику что и для добавления
    
    def delete_image(self, image_type: str):
        """Удаление изображения"""
        if not self.current_images.get(image_type):
            messagebox.showwarning("Предупреждение", "Изображение не найдено")
            return
        
        if messagebox.askyesno("Подтверждение", f"Удалить изображение для {image_type}?"):
            try:
                # Удаляем файл
                os.remove(self.current_images[image_type])
                
                # Сбрасываем отображение
                img_label = getattr(self, f"{image_type}_img_label")
                img_label.configure(image="", text="Изображение не загружено")
                img_label.image = None
                
                info_label = getattr(self, f"{image_type}_info_label")
                info_label.configure(text="")
                
                # Удаляем из словаря
                self.current_images[image_type] = None
                
                messagebox.showinfo("Успех", "Изображение удалено")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить изображение: {e}")
    
    def save_image_metadata(self, image_type: str, image_path: str, description: str):
        """Сохранение метаданных изображения"""
        metadata_file = os.path.join(os.path.dirname(image_path), "metadata.json")
        
        metadata = {}
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except:
                pass
        
        metadata[os.path.basename(image_path)] = {
            "description": description,
            "type": image_type,
            "added_at": datetime.now().isoformat()
        }
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения метаданных: {e}")
    
    def start_bot(self):
        """Запуск Telegram бота"""
        try:
            if self.bot_process and self.bot_process.poll() is None:
                messagebox.showwarning("Предупреждение", "Бот уже запущен")
                return
            
            self.bot_process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.bot_status_label.configure(text="✅ Бот запущен")
            self.start_bot_btn.configure(state='disabled')
            self.stop_bot_btn.configure(state='normal')
            
            # Запускаем отслеживание логов в отдельном потоке
            threading.Thread(target=self.monitor_bot_logs, daemon=True).start()
            
            messagebox.showinfo("Успех", "Бот запущен успешно!")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить бота: {e}")
    
    def stop_bot(self):
        """Остановка Telegram бота"""
        try:
            if self.bot_process:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=5)
                self.bot_process = None
            
            self.bot_status_label.configure(text="❌ Бот остановлен")
            self.start_bot_btn.configure(state='normal')
            self.stop_bot_btn.configure(state='disabled')
            
            messagebox.showinfo("Успех", "Бот остановлен")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось остановить бота: {e}")
    
    def restart_bot(self):
        """Перезапуск Telegram бота"""
        self.stop_bot()
        time.sleep(2)
        self.start_bot()
    
    def monitor_bot_logs(self):
        """Мониторинг логов бота"""
        if not self.bot_process:
            return
        
        while self.bot_process and self.bot_process.poll() is None:
            try:
                output = self.bot_process.stdout.readline()
                if output:
                    # Обновляем текстовое поле с логами
                    self.log_text.insert(tk.END, output)
                    self.log_text.see(tk.END)
                    self.root.update_idletasks()
            except:
                break
    
    def add_admin(self):
        """Добавление нового администратора"""
        admin_id = self.admin_id_entry.get().strip()
        if not admin_id:
            messagebox.showwarning("Предупреждение", "Введите ID администратора")
            return
        
        try:
            admin_id = int(admin_id)
            # Здесь должна быть логика добавления админа в базу данных
            self.admins_listbox.insert(tk.END, f"Admin ID: {admin_id}")
            self.admin_id_entry.delete(0, tk.END)
            messagebox.showinfo("Успех", f"Администратор {admin_id} добавлен")
        except ValueError:
            messagebox.showerror("Ошибка", "ID должен быть числом")
    
    def remove_admin(self):
        """Удаление администратора"""
        selection = self.admins_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите администратора для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", "Удалить выбранного администратора?"):
            self.admins_listbox.delete(selection[0])
            messagebox.showinfo("Успех", "Администратор удален")
    
    def start_web_server(self):
        """Запуск веб-сервера"""
        try:
            port = self.port_entry.get() or "5000"
            
            if self.web_process and self.web_process.poll() is None:
                messagebox.showwarning("Предупреждение", "Веб-сервер уже запущен")
                return
            
            # Создаем веб-приложение, если его нет
            self.create_web_app()
            
            self.web_process = subprocess.Popen(
                [sys.executable, "web_app.py", "--port", port],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            
            self.web_status_label.configure(text=f"✅ Веб-сервер запущен на порту {port}")
            messagebox.showinfo("Успех", f"Веб-сервер запущен на http://localhost:{port}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить веб-сервер: {e}")
    
    def stop_web_server(self):
        """Остановка веб-сервера"""
        try:
            if self.web_process:
                self.web_process.terminate()
                self.web_process.wait(timeout=5)
                self.web_process = None
            
            self.web_status_label.configure(text="❌ Веб-сервер остановлен")
            messagebox.showinfo("Успех", "Веб-сервер остановлен")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось остановить веб-сервер: {e}")
    
    def open_web_interface(self):
        """Открытие веб-интерфейса в браузере"""
        port = self.port_entry.get() or "5000"
        url = f"http://localhost:{port}"
        webbrowser.open(url)
    
    def create_web_app(self):
        """Создание файла веб-приложения"""
        web_app_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Веб-интерфейс для RUУчебник
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
import argparse

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory('images', filename)

@app.route('/api/images')
def get_images():
    images = {}
    images_dir = 'images'
    
    if os.path.exists(images_dir):
        for subdir in os.listdir(images_dir):
            subdir_path = os.path.join(images_dir, subdir)
            if os.path.isdir(subdir_path):
                images[subdir] = []
                for file in os.listdir(subdir_path):
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                        images[subdir].append(file)
    
    return jsonify(images)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()
    
    app.run(host='0.0.0.0', port=args.port, debug=True)
'''
        
        if not os.path.exists("web_app.py"):
            with open("web_app.py", 'w', encoding='utf-8') as f:
                f.write(web_app_content)
        
        # Создаем директорию templates и базовый HTML
        if not os.path.exists("templates"):
            os.makedirs("templates")
        
        html_content = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RUУчебник - Веб-интерфейс</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f0f0; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; color: #001F3F; margin-bottom: 30px; }
        .section { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .image-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .image-item { text-align: center; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }
        .image-item img { max-width: 200px; max-height: 200px; border-radius: 4px; }
        .menu-buttons { display: flex; justify-content: center; gap: 20px; margin: 30px 0; }
        .btn { padding: 15px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-size: 16px; }
        .btn:hover { background: #45a049; }
        .solver-btn { background: #ff9800; }
        .textbooks-btn { background: #2196F3; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 RUУчебник - Веб-интерфейс</h1>
            <p>Система поиска и управления школьными учебниками</p>
        </div>
        
        <div class="menu-buttons">
            <a href="#" class="btn solver-btn" onclick="showSoon()">🧮 Решатор</a>
            <a href="#textbooks" class="btn textbooks-btn">📚 Учебники</a>
        </div>
        
        <div class="section">
            <h2>📊 Статус системы</h2>
            <p>Веб-интерфейс работает корректно</p>
        </div>
        
        <div class="section">
            <h2>🖼️ Управление изображениями</h2>
            <div id="images-container">
                <p>Загрузка изображений...</p>
            </div>
        </div>
    </div>
    
    <script>
        function showSoon() {
            alert('Soon...');
        }
        
        // Загрузка изображений
        fetch('/api/images')
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('images-container');
                let html = '<div class="image-grid">';
                
                for (const [category, images] of Object.entries(data)) {
                    if (images.length > 0) {
                        html += `<div class="image-item">
                            <h3>${category.charAt(0).toUpperCase() + category.slice(1)}</h3>`;
                        for (const image of images) {
                            html += `<img src="/images/${category}/${image}" alt="${category}" title="${image}">`;
                        }
                        html += '</div>';
                    }
                }
                
                html += '</div>';
                container.innerHTML = html;
            })
            .catch(error => {
                document.getElementById('images-container').innerHTML = '<p>Ошибка загрузки изображений</p>';
            });
    </script>
</body>
</html>'''
        
        if not os.path.exists("templates/index.html"):
            with open("templates/index.html", 'w', encoding='utf-8') as f:
                f.write(html_content)
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

if __name__ == "__main__":
    app = RUUchebnikDesktopApp()
    app.run()