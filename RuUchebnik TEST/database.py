# -*- coding: utf-8 -*-
"""
Модуль для работы с базой данных PostgreSQL
Содержит все операции для работы с пользователями, учебниками и статистикой

Автор: Разработано для системы RUУчебник
Версия: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import asyncpg
from asyncpg import Pool, Connection

from config import BOT_CONFIG


class DatabaseManager:
    """Менеджер для работы с базой данных PostgreSQL"""
    
    def __init__(self):
        """Инициализация менеджера базы данных"""
        self.pool: Optional[Pool] = None
        self.logger = logging.getLogger(__name__)
        self.database_url = BOT_CONFIG['database_url']
        
        if not self.database_url:
            raise ValueError("DATABASE_URL не установлен в конфигурации")
    
    async def initialize(self) -> None:
        """
        Инициализация пула соединений с базой данных
        
        Raises:
            Exception: Если не удалось подключиться к базе данных
        """
        try:
            # Создание пула соединений
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=30,
                server_settings={'application_name': 'ruuchebnik_bot'}
            )
            
            self.logger.info("✅ Пул соединений с базой данных создан успешно")
            
            # Проверка подключения
            async with self.pool.acquire() as connection:
                version = await connection.fetchval('SELECT version()')
                self.logger.info(f"📊 Подключено к: {version.split(',')[0]}")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            raise
    
    async def close(self) -> None:
        """Закрытие пула соединений с базой данных"""
        if self.pool:
            await self.pool.close()
            self.logger.info("📊 Пул соединений с базой данных закрыт")
    
    # =============================================================================
    # РАБОТА С ПОЛЬЗОВАТЕЛЯМИ БОТА
    # =============================================================================
    
    async def get_or_create_user(self, telegram_id: int, username: Optional[str] = None, 
                                first_name: Optional[str] = None, 
                                last_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Получение или создание пользователя бота
        
        Args:
            telegram_id: ID пользователя в Telegram
            username: Имя пользователя в Telegram (без @)
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            
        Returns:
            Dict: Данные пользователя
        """
        async with self.pool.acquire() as connection:
            # Проверяем, существует ли пользователь
            user = await connection.fetchrow(
                "SELECT * FROM bot_users WHERE telegram_id = $1",
                str(telegram_id)
            )
            
            if user:
                # Обновляем информацию о пользователе
                await connection.execute("""
                    UPDATE bot_users 
                    SET username = $2, first_name = $3, last_name = $4, 
                        last_activity_at = CURRENT_TIMESTAMP 
                    WHERE telegram_id = $1
                """, str(telegram_id), username, first_name, last_name)
                
                # Получаем обновленные данные
                user = await connection.fetchrow(
                    "SELECT * FROM bot_users WHERE telegram_id = $1",
                    str(telegram_id)
                )
            else:
                # Создаем нового пользователя
                user = await connection.fetchrow("""
                    INSERT INTO bot_users (telegram_id, username, first_name, last_name)
                    VALUES ($1, $2, $3, $4)
                    RETURNING *
                """, str(telegram_id), username, first_name, last_name)
                
                self.logger.info(f"👤 Создан новый пользователь: {telegram_id} (@{username})")
            
            return dict(user) if user else {}
    
    async def update_user_activity(self, telegram_id: int) -> None:
        """
        Обновление времени последней активности пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
        """
        async with self.pool.acquire() as connection:
            await connection.execute(
                "UPDATE bot_users SET last_activity_at = CURRENT_TIMESTAMP WHERE telegram_id = $1",
                str(telegram_id)
            )
    
    async def is_user_blocked(self, telegram_id: int) -> bool:
        """
        Проверка, заблокирован ли пользователь
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            bool: True если пользователь заблокирован
        """
        async with self.pool.acquire() as connection:
            result = await connection.fetchval(
                "SELECT is_blocked FROM bot_users WHERE telegram_id = $1",
                str(telegram_id)
            )
            return bool(result)
    
    async def increment_user_downloads(self, telegram_id: int) -> None:
        """
        Увеличение счетчика скачиваний пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
        """
        async with self.pool.acquire() as connection:
            await connection.execute("""
                UPDATE bot_users 
                SET download_count = download_count + 1,
                    last_activity_at = CURRENT_TIMESTAMP
                WHERE telegram_id = $1
            """, str(telegram_id))
    
    # =============================================================================
    # РАБОТА С УЧЕБНИКАМИ
    # =============================================================================
    
    async def get_classes(self) -> List[Dict[str, Any]]:
        """
        Получение списка всех доступных классов
        
        Returns:
            List[Dict]: Список классов
        """
        async with self.pool.acquire() as connection:
            rows = await connection.fetch("""
                SELECT * FROM classes 
                WHERE is_active = true 
                ORDER BY display_order
            """)
            return [dict(row) for row in rows]
    
    async def get_subjects_by_class(self, class_id: str) -> List[Dict[str, Any]]:
        """
        Получение предметов для определенного класса
        
        Args:
            class_id: ID класса
            
        Returns:
            List[Dict]: Список предметов
        """
        async with self.pool.acquire() as connection:
            rows = await connection.fetch("""
                SELECT DISTINCT s.* FROM subjects s
                JOIN textbooks t ON t.subject_id = s.id
                WHERE t.class_id = $1 AND t.is_active = true AND s.is_active = true
                ORDER BY s.display_order
            """, class_id)
            return [dict(row) for row in rows]
    
    async def get_textbooks(self, class_id: str, subject_id: str) -> List[Dict[str, Any]]:
        """
        Получение учебников по классу и предмету
        
        Args:
            class_id: ID класса
            subject_id: ID предмета
            
        Returns:
            List[Dict]: Список учебников с информацией об авторах
        """
        async with self.pool.acquire() as connection:
            rows = await connection.fetch("""
                SELECT 
                    t.*,
                    a.full_name as author_name,
                    a.short_name as author_short_name,
                    c.name as class_name,
                    s.name as subject_name
                FROM textbooks t
                LEFT JOIN authors a ON t.author_id = a.id
                LEFT JOIN classes c ON t.class_id = c.id  
                LEFT JOIN subjects s ON t.subject_id = s.id
                WHERE t.class_id = $1 AND t.subject_id = $2 AND t.is_active = true
                ORDER BY t.title, t.uploaded_at DESC
            """, class_id, subject_id)
            return [dict(row) for row in rows]
    
    async def get_textbook(self, textbook_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации об учебнике по ID
        
        Args:
            textbook_id: ID учебника
            
        Returns:
            Optional[Dict]: Информация об учебнике или None
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow("""
                SELECT 
                    t.*,
                    a.full_name as author_name,
                    a.short_name as author_short_name,
                    c.name as class_name,
                    s.name as subject_name
                FROM textbooks t
                LEFT JOIN authors a ON t.author_id = a.id
                LEFT JOIN classes c ON t.class_id = c.id
                LEFT JOIN subjects s ON t.subject_id = s.id
                WHERE t.id = $1 AND t.is_active = true
            """, textbook_id)
            return dict(row) if row else None
    
    async def increment_textbook_downloads(self, textbook_id: str) -> None:
        """
        Увеличение счетчика скачиваний учебника
        
        Args:
            textbook_id: ID учебника
        """
        async with self.pool.acquire() as connection:
            await connection.execute(
                "UPDATE textbooks SET download_count = download_count + 1 WHERE id = $1",
                textbook_id
            )
    
    async def search_textbooks(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Поиск учебников по названию
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            
        Returns:
            List[Dict]: Найденные учебники
        """
        async with self.pool.acquire() as connection:
            rows = await connection.fetch("""
                SELECT 
                    t.*,
                    a.full_name as author_name,
                    a.short_name as author_short_name,
                    c.name as class_name,
                    s.name as subject_name
                FROM textbooks t
                LEFT JOIN authors a ON t.author_id = a.id
                LEFT JOIN classes c ON t.class_id = c.id
                LEFT JOIN subjects s ON t.subject_id = s.id
                WHERE t.is_active = true 
                    AND (
                        LOWER(t.title) LIKE LOWER($1) 
                        OR LOWER(a.full_name) LIKE LOWER($1)
                        OR LOWER(a.short_name) LIKE LOWER($1)
                    )
                ORDER BY t.download_count DESC, t.title
                LIMIT $2
            """, f"%{query}%", limit)
            return [dict(row) for row in rows]
    
    # =============================================================================
    # РЕГИСТРАЦИЯ СКАЧИВАНИЙ
    # =============================================================================
    
    async def log_download(self, user_id: str, textbook_id: str, 
                          ip_address: Optional[str] = None) -> None:
        """
        Логирование скачивания учебника
        
        Args:
            user_id: ID пользователя
            textbook_id: ID учебника
            ip_address: IP адрес (опционально)
        """
        async with self.pool.acquire() as connection:
            await connection.execute("""
                INSERT INTO downloads (user_id, textbook_id, ip_address)
                VALUES ($1, $2, $3)
            """, user_id, textbook_id, ip_address)
    
    # =============================================================================
    # СТАТИСТИКА
    # =============================================================================
    
    async def get_bot_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики бота
        
        Returns:
            Dict: Статистические данные
        """
        async with self.pool.acquire() as connection:
            # Общая статистика
            stats = {}
            
            # Общее количество пользователей
            stats['total_users'] = await connection.fetchval(
                "SELECT COUNT(*) FROM bot_users"
            )
            
            # Активные пользователи сегодня
            today = datetime.now().date()
            stats['active_today'] = await connection.fetchval(
                "SELECT COUNT(*) FROM bot_users WHERE DATE(last_activity_at) = $1",
                today
            )
            
            # Новые пользователи за последние 7 дней
            week_ago = datetime.now() - timedelta(days=7)
            stats['new_users_week'] = await connection.fetchval(
                "SELECT COUNT(*) FROM bot_users WHERE registered_at >= $1",
                week_ago
            )
            
            # Общее количество учебников
            stats['total_textbooks'] = await connection.fetchval(
                "SELECT COUNT(*) FROM textbooks WHERE is_active = true"
            )
            
            # Общее количество скачиваний
            stats['total_downloads'] = await connection.fetchval(
                "SELECT SUM(download_count) FROM textbooks"
            )
            
            # Скачивания сегодня
            stats['downloads_today'] = await connection.fetchval(
                "SELECT COUNT(*) FROM downloads WHERE DATE(downloaded_at) = $1",
                today
            )
            
            # Популярные предметы (топ 5)
            popular_subjects = await connection.fetch("""
                SELECT s.name, SUM(t.download_count) as downloads
                FROM subjects s
                JOIN textbooks t ON t.subject_id = s.id
                WHERE t.is_active = true
                GROUP BY s.id, s.name
                ORDER BY downloads DESC
                LIMIT 5
            """)
            stats['popular_subjects'] = [dict(row) for row in popular_subjects]
            
            return stats
    
    async def get_user_statistics(self, telegram_id: int) -> Dict[str, Any]:
        """
        Получение статистики конкретного пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Dict: Статистика пользователя
        """
        async with self.pool.acquire() as connection:
            user_stats = {}
            user_id = await connection.fetchval(
                "SELECT id FROM bot_users WHERE telegram_id = $1",
                str(telegram_id)
            )
            
            if not user_id:
                return {}
            
            # Общее количество скачиваний пользователя
            user_stats['total_downloads'] = await connection.fetchval(
                "SELECT download_count FROM bot_users WHERE id = $1",
                user_id
            )
            
            # Скачивания за сегодня
            today = datetime.now().date()
            user_stats['downloads_today'] = await connection.fetchval(
                "SELECT COUNT(*) FROM downloads WHERE user_id = $1 AND DATE(downloaded_at) = $2",
                user_id, today
            )
            
            # Любимые предметы пользователя
            favorite_subjects = await connection.fetch("""
                SELECT s.name, COUNT(*) as count
                FROM downloads d
                JOIN textbooks t ON d.textbook_id = t.id
                JOIN subjects s ON t.subject_id = s.id
                WHERE d.user_id = $1
                GROUP BY s.id, s.name
                ORDER BY count DESC
                LIMIT 3
            """, user_id)
            user_stats['favorite_subjects'] = [dict(row) for row in favorite_subjects]
            
            return user_stats
    
    # =============================================================================
    # СИСТЕМНЫЕ ЛОГИ
    # =============================================================================
    
    async def log_system_event(self, event_type: str, action: str, 
                              details: Optional[Dict] = None, 
                              user_id: Optional[str] = None) -> None:
        """
        Логирование системного события
        
        Args:
            event_type: Тип события (info, warning, error)
            action: Описание действия
            details: Дополнительные детали в формате JSON
            user_id: ID пользователя (если применимо)
        """
        async with self.pool.acquire() as connection:
            await connection.execute("""
                INSERT INTO system_logs (type, action, details, user_id)
                VALUES ($1, $2, $3, $4)
            """, event_type, action, details, user_id)
    
    # =============================================================================
    # АДМИНИСТРАТИВНЫЕ ФУНКЦИИ
    # =============================================================================
    
    async def get_all_user_ids(self) -> List[int]:
        """
        Получение всех telegram_id пользователей для рассылки
        
        Returns:
            List[int]: Список telegram_id пользователей
        """
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(
                "SELECT telegram_id FROM bot_users WHERE is_blocked = false"
            )
            return [int(row['telegram_id']) for row in rows]
    
    async def block_user(self, telegram_id: int, reason: str = "") -> bool:
        """
        Блокировка пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            reason: Причина блокировки
            
        Returns:
            bool: True если пользователь заблокирован
        """
        async with self.pool.acquire() as connection:
            result = await connection.execute(
                "UPDATE bot_users SET is_blocked = true WHERE telegram_id = $1",
                str(telegram_id)
            )
            
            if result != "UPDATE 0":
                await self.log_system_event(
                    "warning", 
                    f"Пользователь {telegram_id} заблокирован",
                    {"reason": reason}
                )
                return True
            return False
    
    async def unblock_user(self, telegram_id: int) -> bool:
        """
        Разблокировка пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            bool: True если пользователь разблокирован
        """
        async with self.pool.acquire() as connection:
            result = await connection.execute(
                "UPDATE bot_users SET is_blocked = false WHERE telegram_id = $1",
                str(telegram_id)
            )
            
            if result != "UPDATE 0":
                await self.log_system_event(
                    "info",
                    f"Пользователь {telegram_id} разблокирован"
                )
                return True
            return False


# Глобальный экземпляр менеджера базы данных
db_manager: Optional[DatabaseManager] = None


async def get_db() -> DatabaseManager:
    """
    Получение экземпляра менеджера базы данных
    
    Returns:
        DatabaseManager: Инициализированный менеджер БД
    """
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
        await db_manager.initialize()
    return db_manager
