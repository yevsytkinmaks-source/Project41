import asyncio
import asyncpg
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bot.config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool created successfully")
            await self._ensure_tables()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def _ensure_tables(self):
        """Ensure all required tables exist"""
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
            telegram_id VARCHAR NOT NULL UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_at TIMESTAMP DEFAULT NOW(),
            downloads INTEGER DEFAULT 0,
            agreed BOOLEAN DEFAULT FALSE,
            last_active TIMESTAMP DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS banned_users (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
            telegram_id VARCHAR NOT NULL UNIQUE,
            reason TEXT NOT NULL,
            banned_at TIMESTAMP DEFAULT NOW(),
            banned_until TIMESTAMP,
            banned_by VARCHAR NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS textbooks (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            subject TEXT NOT NULL,
            grade TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            downloads INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            uploaded_by VARCHAR NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS logs (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
            type TEXT NOT NULL,
            user_id VARCHAR,
            action TEXT NOT NULL,
            details JSONB,
            timestamp TIMESTAMP DEFAULT NOW(),
            ip_address TEXT
        );
        
        CREATE TABLE IF NOT EXISTS broadcasts (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
            message TEXT NOT NULL,
            image_url TEXT,
            sent_to INTEGER NOT NULL,
            sent_by VARCHAR NOT NULL,
            sent_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_banned_users_telegram_id ON banned_users(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_textbooks_grade_subject ON textbooks(grade, subject);
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_logs_type ON logs(type);
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(create_tables_sql)
            logger.info("Database tables ensured")
    
    # User Management
    async def get_user(self, telegram_id: str) -> Optional[Dict]:
        """Get user by telegram ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1",
                telegram_id
            )
            return dict(row) if row else None
    
    async def create_user(self, telegram_id: str, username: str = None, 
                         first_name: str = None, last_name: str = None) -> Dict:
        """Create new user"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (telegram_id, username, first_name, last_name, agreed)
                VALUES ($1, $2, $3, $4, FALSE)
                RETURNING *
                """,
                telegram_id, username, first_name, last_name
            )
            await self.log_action("user_action", telegram_id, "user_registered", {
                "username": username,
                "first_name": first_name,
                "last_name": last_name
            })
            return dict(row)
    
    async def update_user_agreement(self, telegram_id: str) -> None:
        """Mark user as agreed to rules"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET agreed = TRUE, last_active = NOW() WHERE telegram_id = $1",
                telegram_id
            )
            await self.log_action("user_action", telegram_id, "rules_accepted")
    
    async def update_user_activity(self, telegram_id: str) -> None:
        """Update user last activity"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_active = NOW() WHERE telegram_id = $1",
                telegram_id
            )
    
    async def increment_user_downloads(self, telegram_id: str) -> None:
        """Increment user download count"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET downloads = downloads + 1, last_active = NOW() WHERE telegram_id = $1",
                telegram_id
            )
    
    # Ban Management
    async def is_user_banned(self, telegram_id: str) -> Optional[Dict]:
        """Check if user is banned"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM banned_users 
                WHERE telegram_id = $1 
                AND (banned_until IS NULL OR banned_until > NOW())
                """,
                telegram_id
            )
            return dict(row) if row else None
    
    async def ban_user(self, telegram_id: str, reason: str, days: int = None, banned_by: str = None) -> None:
        """Ban user"""
        banned_until = None
        if days:
            banned_until = datetime.now() + timedelta(days=days)
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO banned_users (telegram_id, reason, banned_until, banned_by)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (telegram_id) 
                DO UPDATE SET reason = $2, banned_until = $3, banned_by = $4, banned_at = NOW()
                """,
                telegram_id, reason, banned_until, banned_by or "system"
            )
            await self.log_action("ban", telegram_id, "user_banned", {
                "reason": reason,
                "days": days,
                "banned_by": banned_by
            })
    
    async def unban_user(self, telegram_id: str) -> bool:
        """Unban user"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM banned_users WHERE telegram_id = $1",
                telegram_id
            )
            if result == "DELETE 1":
                await self.log_action("admin_action", telegram_id, "user_unbanned")
                return True
            return False
    
    # Textbook Management
    async def get_textbooks_by_grade(self, grade: str) -> List[Dict]:
        """Get textbooks by grade"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM textbooks WHERE grade = $1 ORDER BY subject, title",
                grade
            )
            return [dict(row) for row in rows]
    
    async def get_textbooks_by_grade_and_subject(self, grade: str, subject: str) -> List[Dict]:
        """Get textbooks by grade and subject"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM textbooks WHERE grade = $1 AND subject = $2 ORDER BY title",
                grade, subject
            )
            return [dict(row) for row in rows]
    
    async def get_textbook(self, textbook_id: str) -> Optional[Dict]:
        """Get textbook by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM textbooks WHERE id = $1",
                textbook_id
            )
            return dict(row) if row else None
    
    async def increment_textbook_downloads(self, textbook_id: str) -> None:
        """Increment textbook download count"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE textbooks SET downloads = downloads + 1 WHERE id = $1",
                textbook_id
            )
    
    async def get_subjects_by_grade(self, grade: str) -> List[str]:
        """Get unique subjects for a grade"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT subject FROM textbooks WHERE grade = $1 ORDER BY subject",
                grade
            )
            return [row['subject'] for row in rows]
    
    # Statistics
    async def get_stats(self) -> Dict:
        """Get system statistics"""
        async with self.pool.acquire() as conn:
            # Total users
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            
            # Total textbooks
            total_textbooks = await conn.fetchval("SELECT COUNT(*) FROM textbooks")
            
            # Active today
            active_today = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE last_active >= CURRENT_DATE"
            )
            
            # Total downloads
            total_downloads = await conn.fetchval(
                "SELECT COALESCE(SUM(downloads), 0) FROM textbooks"
            ) or 0
            
            # Requests today
            requests_today = await conn.fetchval(
                "SELECT COUNT(*) FROM logs WHERE timestamp >= CURRENT_DATE"
            ) or 0
            
            return {
                "total_users": total_users,
                "total_textbooks": total_textbooks,
                "active_today": active_today,
                "total_downloads": total_downloads,
                "requests_today": requests_today
            }
    
    # Logging
    async def log_action(self, log_type: str, user_id: str = None, action: str = "", 
                        details: Dict = None, ip_address: str = None) -> None:
        """Log an action"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO logs (type, user_id, action, details, ip_address)
                VALUES ($1, $2, $3, $4, $5)
                """,
                log_type, user_id, action, json.dumps(details) if details else None, ip_address
            )
    
    async def get_recent_logs(self, limit: int = 50, log_type: str = None) -> List[Dict]:
        """Get recent logs"""
        async with self.pool.acquire() as conn:
            if log_type:
                rows = await conn.fetch(
                    "SELECT * FROM logs WHERE type = $1 ORDER BY timestamp DESC LIMIT $2",
                    log_type, limit
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM logs ORDER BY timestamp DESC LIMIT $1",
                    limit
                )
            return [dict(row) for row in rows]
    
    # Broadcast
    async def save_broadcast(self, message: str, sent_to: int, sent_by: str, image_url: str = None) -> str:
        """Save broadcast record"""
        async with self.pool.acquire() as conn:
            broadcast_id = await conn.fetchval(
                """
                INSERT INTO broadcasts (message, image_url, sent_to, sent_by)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                message, image_url, sent_to, sent_by
            )
            await self.log_action("admin_action", sent_by, "broadcast_sent", {
                "message_length": len(message),
                "sent_to": sent_to,
                "has_image": bool(image_url)
            })
            return broadcast_id
    
    async def get_all_user_ids(self) -> List[str]:
        """Get all user telegram IDs for broadcasting"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT telegram_id FROM users WHERE agreed = TRUE")
            return [row['telegram_id'] for row in rows]

# Global database instance
db = DatabaseManager()
