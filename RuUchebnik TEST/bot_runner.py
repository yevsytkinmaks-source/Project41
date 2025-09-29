#!/usr/bin/env python3
"""
RUУчебник Bot Runner
Главный запуск системы: Telegram бот + веб-панель
"""

import os
import sys
import subprocess
import signal
import time
import asyncio
import threading
import logging
from datetime import datetime
from typing import Optional, List

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ruuchebnik.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RUUchebnikRunner:
    """Управляет запуском всех компонентов системы"""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.running = False
        
        # Проверяем переменные окружения
        self.check_environment()
        
    def check_environment(self):
        """Проверка необходимых переменных окружения"""
        required_vars = [
            'BOT_TOKEN',
            'DATABASE_URL',
            'ADMIN_ID'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
            logger.info("Создайте файл .env со следующими переменными:")
            logger.info("BOT_TOKEN=ваш_токен_бота")
            logger.info("DATABASE_URL=postgresql://user:password@host:port/database")
            logger.info("ADMIN_ID=ваш_telegram_id")
            logger.info("ADMIN_PASSWORD=пароль_админ_панели")
            sys.exit(1)
    
    def start_web_server(self):
        """Запуск веб-сервера"""
        logger.info("🌐 Запуск веб-сервера...")
        
        try:
            # Проверяем наличие node_modules
            if not os.path.exists('node_modules'):
                logger.info("Установка зависимостей Node.js...")
                subprocess.run(['npm', 'install'], check=True)
            
            # Запускаем веб-сервер
            process = subprocess.Popen(
                ['npm', 'run', 'dev'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                env={**os.environ, 'PORT': '5000'}
            )
            
            self.processes.append(process)
            
            # Мониторинг вывода веб-сервера в отдельном потоке
            threading.Thread(
                target=self._monitor_process_output,
                args=(process, "WEB"),
                daemon=True
            ).start()
            
            logger.info("✅ Веб-сервер запущен на http://localhost:5000")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Ошибка запуска веб-сервера: {e}")
            return False
        except FileNotFoundError:
            logger.error("❌ Node.js не найден. Установите Node.js 18+")
            return False
    
    def start_telegram_bot(self):
        """Запуск Telegram бота"""
        logger.info("🤖 Запуск Telegram бота...")
        
        try:
            # Проверяем Python зависимости
            try:
                import telegram
                import asyncpg
            except ImportError as e:
                logger.error(f"❌ Отсутствуют Python зависимости: {e}")
                logger.info("Установите зависимости: pip install -r requirements.txt")
                return False
            
            # Запускаем бота
            bot_script = os.path.join('bot', 'telegram_bot.py')
            if not os.path.exists(bot_script):
                logger.error(f"❌ Файл бота не найден: {bot_script}")
                return False
            
            process = subprocess.Popen(
                [sys.executable, bot_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes.append(process)
            
            # Мониторинг вывода бота в отдельном потоке
            threading.Thread(
                target=self._monitor_process_output,
                args=(process, "BOT"),
                daemon=True
            ).start()
            
            logger.info("✅ Telegram бот запущен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска Telegram бота: {e}")
            return False
    
    def _monitor_process_output(self, process: subprocess.Popen, prefix: str):
        """Мониторинг вывода процесса"""
        try:
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    logger.info(f"[{prefix}] {line.strip()}")
                if process.poll() is not None:
                    break
        except Exception as e:
            logger.error(f"Ошибка мониторинга процесса {prefix}: {e}")
        
        # Процесс завершился
        if process.poll() is not None:
            logger.warning(f"[{prefix}] Процесс завершился с кодом {process.poll()}")
    
    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        def signal_handler(signum, frame):
            logger.info(f"Получен сигнал {signum}, завершение работы...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self):
        """Запуск всей системы"""
        logger.info("🚀 Запуск RUУчебник системы...")
        logger.info(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.setup_signal_handlers()
        self.running = True
        
        # Запускаем компоненты
        web_started = self.start_web_server()
        bot_started = self.start_telegram_bot()
        
        if not web_started and not bot_started:
            logger.error("❌ Не удалось запустить ни один компонент!")
            return False
        
        logger.info("🎉 Система запущена!")
        logger.info("🌐 Веб админ-панель: http://localhost:5000")
        logger.info("🔑 Пароль админ-панели: 14101988")
        logger.info("🤖 Telegram бот: работает")
        logger.info("📊 Мониторинг: логи в файле ruuchebnik.log")
        
        # Ожидание завершения
        try:
            while self.running and any(p.poll() is None for p in self.processes):
                time.sleep(1)
                
                # Проверяем статус процессов
                for i, process in enumerate(self.processes):
                    if process.poll() is not None:
                        component = "WEB" if i == 0 else "BOT"
                        logger.warning(f"Компонент {component} неожиданно завершился")
                        
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания...")
        
        self.stop()
        return True
    
    def stop(self):
        """Остановка всей системы"""
        logger.info("🛑 Остановка системы...")
        self.running = False
        
        for i, process in enumerate(self.processes):
            if process.poll() is None:
                component = "WEB" if i == 0 else "BOT"
                logger.info(f"Останавливаем {component}...")
                
                try:
                    process.terminate()
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Принудительное завершение {component}...")
                    process.kill()
                except Exception as e:
                    logger.error(f"Ошибка при остановке {component}: {e}")
        
        self.processes.clear()
        logger.info("✅ Система остановлена")
    
    def status(self):
        """Показать статус системы"""
        print("📊 Статус RUУчебник системы")
        print("=" * 40)
        print(f"Запущенных процессов: {len([p for p in self.processes if p.poll() is None])}")
        
        for i, process in enumerate(self.processes):
            component = "WEB-СЕРВЕР" if i == 0 else "TELEGRAM-БОТ"
            status = "✅ Работает" if process.poll() is None else "❌ Остановлен"
            print(f"{component}: {status}")
        
        if self.processes:
            print("\n🌐 Веб админ-панель: http://localhost:5000")
            print("🔑 Пароль: 14101988")

def main():
    """Главная функция"""
    if len(sys.argv) > 1 and sys.argv[1] == '--status':
        # Показать статус (упрощенная версия)
        print("Для просмотра статуса запустите веб админ-панель")
        return
    
    # Приветственное сообщение
    print("=" * 60)
    print("🎓 RUУчебник - Образовательный Telegram бот")
    print("📚 Система управления школьными учебниками")
    print("=" * 60)
    print()
    
    runner = RUUchebnikRunner()
    
    try:
        runner.start()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
