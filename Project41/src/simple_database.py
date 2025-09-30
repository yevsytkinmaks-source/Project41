# -*- coding: utf-8 -*-
"""
Упрощенная версия менеджера базы данных для демонстрации
"""

import asyncio
import logging
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

class DatabaseManager:
    """Упрощенный менеджер базы данных"""
    
    def __init__(self):
        self.db_path = "bot_database.db"
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Инициализация базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_blocked BOOLEAN DEFAULT FALSE
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS textbooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    author TEXT,
                    class_name TEXT,
                    subject TEXT,
                    file_path TEXT,
                    downloads INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
            conn.close()
            self.logger.info("✅ База данных инициализирована")
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise
    
    async def close(self):
        """Закрытие соединения"""
        self.logger.info("📊 База данных закрыта")
    
    async def get_or_create_user(self, telegram_id: int, username: str = None, 
                                first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """Получение или создание пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, существует ли пользователь
            cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            user = cursor.fetchone()
            
            if not user:
                # Создаем нового пользователя
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, username, first_name, last_name))
                conn.commit()
                self.logger.info(f"👤 Создан новый пользователь: {telegram_id}")
            
            conn.close()
            return {
                'telegram_id': telegram_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'is_new': not bool(user)
            }
        except Exception as e:
            self.logger.error(f"❌ Ошибка работы с пользователем: {e}")
            return {}
    
    async def is_user_blocked(self, telegram_id: int) -> bool:
        """Проверка, заблокирован ли пользователь"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT is_blocked FROM users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            conn.close()
            return bool(result and result[0]) if result else False
        except:
            return False
    
    async def get_textbooks_by_class_and_subject(self, class_name: str, subject: str) -> List[Dict]:
        """Получение учебников по классу и предмету"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, author, class_name, subject, downloads
                FROM textbooks 
                WHERE class_name = ? AND subject = ?
            ''', (class_name, subject))
            
            textbooks = []
            for row in cursor.fetchall():
                textbooks.append({
                    'id': row[0],
                    'title': row[1],
                    'author': row[2],
                    'class_name': row[3],
                    'subject': row[4],
                    'downloads': row[5]
                })
            
            conn.close()
            return textbooks
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения учебников: {e}")
            return []
    
    async def increment_download_count(self, textbook_id: int):
        """Увеличение счетчика скачиваний"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE textbooks SET downloads = downloads + 1 WHERE id = ?
            ''', (textbook_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления счетчика: {e}")