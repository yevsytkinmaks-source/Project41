#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный запускающий файл для системы RUУчебник
Автоматически запускает бота и десктопное приложение
"""

import sys
import os
import threading
import subprocess
import time
import tkinter as tk
from tkinter import messagebox
import asyncio

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def run_bot():
    """Запуск Telegram бота в отдельном процессе"""
    try:
        from src import enhanced_bot
        asyncio.run(enhanced_bot.main())
    except Exception as e:
        print(f"Ошибка запуска бота: {e}")

def run_desktop_app():
    """Запуск десктопного приложения"""
    try:
        from src.enhanced_desktop_app import RUUchebnikDesktopApp
        app = RUUchebnikDesktopApp()
        app.run()
    except Exception as e:
        print(f"Ошибка запуска десктопного приложения: {e}")
        # Показываем уведомление об ошибке
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Ошибка", f"Не удалось запустить десктопное приложение: {e}")
        root.destroy()

def main():
    """Главная функция запуска системы"""
    print("🚀 Запуск системы RUУчебник...")
    print("=" * 50)
    
    # Создаем директории если их нет
    directories = ["images", "images/rules", "images/solver", "images/textbooks", "images/help", "templates"]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Создана директория: {directory}")
    
    # Запускаем бота в отдельном потоке
    print("🤖 Запуск Telegram бота...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Небольшая задержка
    time.sleep(2)
    
    # Запускаем десктопное приложение в главном потоке
    print("🖥️ Запуск десктопного приложения...")
    run_desktop_app()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Система остановлена пользователем")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        sys.exit(1)