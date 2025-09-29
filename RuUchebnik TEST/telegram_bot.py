import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters,
    ContextTypes
)
from telegram.error import TelegramError
from bot.config import (
    BOT_TOKEN, ADMIN_ID, RULES_TEXT, HELP_TEXT, ABOUT_TEXT,
    ERROR_MESSAGES, SUCCESS_MESSAGES, KEYBOARD_TEXTS,
    CLASSES, SUBJECTS, ADMIN_COMMANDS
)
from bot.database import db

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class RUUchebnikBot:
    def __init__(self):
        self.application = None
    
    async def initialize(self):
        """Initialize bot and database"""
        await db.initialize()
        
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        self.add_handlers()
        
        # Set bot commands
        await self.set_bot_commands()
        
        logger.info("Bot initialized successfully")
    
    def add_handlers(self):
        """Add all bot handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("textbooks", self.textbooks_command))
        self.application.add_handler(CommandHandler("about", self.about_command))
        
        # Admin commands
        self.application.add_handler(CommandHandler("stats", self.admin_stats))
        self.application.add_handler(CommandHandler("users", self.admin_users))
        self.application.add_handler(CommandHandler("broadcast", self.admin_broadcast))
        self.application.add_handler(CommandHandler("ban", self.admin_ban))
        self.application.add_handler(CommandHandler("unban", self.admin_unban))
        self.application.add_handler(CommandHandler("logs", self.admin_logs))
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handler for broadcasts
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def set_bot_commands(self):
        """Set bot commands in menu"""
        commands = [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("help", "Помощь и инструкции"),
            BotCommand("textbooks", "Найти учебники"),
            BotCommand("about", "О боте"),
        ]
        await self.application.bot.set_my_commands(commands)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Check if user is banned
        ban_info = await db.is_user_banned(str(user.id))
        if ban_info:
            await update.message.reply_text(
                ERROR_MESSAGES["banned"].format(
                    reason=ban_info["reason"],
                    until=ban_info["banned_until"].strftime("%d.%m.%Y %H:%M") if ban_info["banned_until"] else "навсегда"
                )
            )
            return
        
        # Get or create user
        user_data = await db.get_user(str(user.id))
        if not user_data:
            user_data = await db.create_user(
                str(user.id),
                user.username,
                user.first_name,
                user.last_name
            )
        
        await db.update_user_activity(str(user.id))
        
        # Check if user agreed to rules
        if not user_data["agreed"]:
            keyboard = [
                [InlineKeyboardButton(KEYBOARD_TEXTS["agree_rules"], callback_data="agree_rules")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                RULES_TEXT,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await self.show_main_menu(update, context)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not await self.check_user_access(update):
            return
        
        await update.message.reply_text(HELP_TEXT, parse_mode='HTML')
    
    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /about command"""
        if not await self.check_user_access(update):
            return
        
        stats = await db.get_stats()
        about_text = ABOUT_TEXT.format(**stats)
        
        await update.message.reply_text(about_text, parse_mode='HTML')
    
    async def textbooks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /textbooks command"""
        if not await self.check_user_access(update):
            return
        
        await self.show_classes_menu(update, context)
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu"""
        keyboard = [
            [InlineKeyboardButton(KEYBOARD_TEXTS["textbooks"], callback_data="menu_textbooks")],
            [InlineKeyboardButton(KEYBOARD_TEXTS["help"], callback_data="menu_help"),
             InlineKeyboardButton(KEYBOARD_TEXTS["about"], callback_data="menu_about")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"🎓 Добро пожаловать в RUУчебник!\n\nВыберите действие:"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                welcome_text,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup
            )
    
    async def show_classes_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show classes selection menu"""
        keyboard = []
        
        # Add class buttons in rows of 3
        class_buttons = []
        for class_id, class_name in CLASSES.items():
            class_buttons.append(InlineKeyboardButton(class_name, callback_data=f"class_{class_id}"))
            
            if len(class_buttons) == 3:
                keyboard.append(class_buttons)
                class_buttons = []
        
        if class_buttons:
            keyboard.append(class_buttons)
        
        keyboard.append([InlineKeyboardButton(KEYBOARD_TEXTS["back"], callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "📚 Выберите класс:"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_subjects_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, grade: str):
        """Show subjects menu for selected grade"""
        subjects = await db.get_subjects_by_grade(grade)
        
        if not subjects:
            await update.callback_query.edit_message_text(
                ERROR_MESSAGES["no_textbooks"],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(KEYBOARD_TEXTS["back"], callback_data="back_to_classes")]
                ])
            )
            return
        
        keyboard = []
        for subject in subjects:
            subject_display = SUBJECTS.get(subject, subject.title())
            keyboard.append([InlineKeyboardButton(
                subject_display, 
                callback_data=f"subject_{grade}_{subject}"
            )])
        
        keyboard.append([InlineKeyboardButton(KEYBOARD_TEXTS["back"], callback_data="back_to_classes")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"📖 Выберите предмет для {CLASSES[grade]}:"
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_textbooks_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 grade: str, subject: str):
        """Show textbooks menu for selected grade and subject"""
        textbooks = await db.get_textbooks_by_grade_and_subject(grade, subject)
        
        if not textbooks:
            await update.callback_query.edit_message_text(
                ERROR_MESSAGES["no_textbooks"],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(KEYBOARD_TEXTS["back"], callback_data=f"class_{grade}")]
                ])
            )
            return
        
        keyboard = []
        for textbook in textbooks:
            button_text = f"📖 {textbook['title']} - {textbook['author']}"
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"textbook_{textbook['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(KEYBOARD_TEXTS["back"], callback_data=f"class_{grade}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        subject_display = SUBJECTS.get(subject, subject.title())
        text = f"📚 {subject_display} - {CLASSES[grade]}:\n\nВыберите учебник:"
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_textbook_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   textbook_id: str):
        """Show textbook details and download option"""
        textbook = await db.get_textbook(textbook_id)
        
        if not textbook:
            await update.callback_query.edit_message_text(
                ERROR_MESSAGES["file_not_found"],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(KEYBOARD_TEXTS["back"], callback_data="back_to_classes")]
                ])
            )
            return
        
        # Format file size
        file_size = ""
        if textbook["file_size"]:
            size_mb = textbook["file_size"] / (1024 * 1024)
            file_size = f"\n📊 Размер: {size_mb:.1f} МБ"
        
        text = f"""
📖 <b>{textbook['title']}</b>

👤 Автор: {textbook['author']}
🎓 Класс: {CLASSES.get(textbook['grade'], textbook['grade'])}
📚 Предмет: {SUBJECTS.get(textbook['subject'], textbook['subject'].title())}
📥 Скачиваний: {textbook['downloads']}{file_size}
"""
        
        keyboard = [
            [InlineKeyboardButton(KEYBOARD_TEXTS["download"], callback_data=f"download_{textbook_id}")],
            [InlineKeyboardButton(KEYBOARD_TEXTS["back"], callback_data=f"subject_{textbook['grade']}_{textbook['subject']}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text, 
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def download_textbook(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               textbook_id: str):
        """Download textbook file"""
        user_id = str(update.effective_user.id)
        textbook = await db.get_textbook(textbook_id)
        
        if not textbook or not os.path.exists(textbook["file_path"]):
            await update.callback_query.answer(ERROR_MESSAGES["file_not_found"], show_alert=True)
            return
        
        try:
            # Send download starting message
            await update.callback_query.answer(SUCCESS_MESSAGES["download_started"])
            
            # Send the file
            with open(textbook["file_path"], 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=textbook["file_name"],
                    caption=f"📖 {textbook['title']}\n👤 {textbook['author']}"
                )
            
            # Update statistics
            await db.increment_textbook_downloads(textbook_id)
            await db.increment_user_downloads(user_id)
            
            # Log download
            await db.log_action("user_action", user_id, "textbook_downloaded", {
                "textbook_id": textbook_id,
                "title": textbook["title"],
                "author": textbook["author"],
                "grade": textbook["grade"],
                "subject": textbook["subject"]
            })
            
        except Exception as e:
            logger.error(f"Error sending textbook {textbook_id}: {e}")
            await update.callback_query.answer(ERROR_MESSAGES["download_error"], show_alert=True)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Check user access for most callbacks
        if data != "agree_rules" and not await self.check_user_access(update):
            return
        
        try:
            if data == "agree_rules":
                user_id = str(update.effective_user.id)
                await db.update_user_agreement(user_id)
                await query.edit_message_text(SUCCESS_MESSAGES["rules_accepted"])
                await asyncio.sleep(1)
                await self.show_main_menu(update, context)
            
            elif data == "menu_textbooks" or data == "back_to_classes":
                await self.show_classes_menu(update, context)
            
            elif data == "menu_help":
                await query.edit_message_text(HELP_TEXT, parse_mode='HTML')
                await asyncio.sleep(3)
                await self.show_main_menu(update, context)
            
            elif data == "menu_about":
                stats = await db.get_stats()
                about_text = ABOUT_TEXT.format(**stats)
                await query.edit_message_text(about_text, parse_mode='HTML')
                await asyncio.sleep(3)
                await self.show_main_menu(update, context)
            
            elif data == "back_to_main":
                await self.show_main_menu(update, context)
            
            elif data.startswith("class_"):
                grade = data.replace("class_", "")
                await self.show_subjects_menu(update, context, grade)
            
            elif data.startswith("subject_"):
                _, grade, subject = data.split("_", 2)
                await self.show_textbooks_menu(update, context, grade, subject)
            
            elif data.startswith("textbook_"):
                textbook_id = data.replace("textbook_", "")
                await self.show_textbook_details(update, context, textbook_id)
            
            elif data.startswith("download_"):
                textbook_id = data.replace("download_", "")
                await self.download_textbook(update, context, textbook_id)
            
            elif data == "solver":
                # Removed solver functionality - show "Soon..." message
                await query.answer(KEYBOARD_TEXTS["soon"], show_alert=True)
        
        except Exception as e:
            logger.error(f"Error in button callback {data}: {e}")
            await query.answer(ERROR_MESSAGES["general_error"], show_alert=True)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        if not await self.check_user_access(update):
            return
        
        user_id = str(update.effective_user.id)
        
        # Check if this is a broadcast response from admin
        if user_id == str(ADMIN_ID) and hasattr(context.user_data, 'waiting_for_broadcast'):
            await self.handle_admin_broadcast_message(update, context)
        else:
            # Regular user message - suggest using menu
            await update.message.reply_text(
                "👋 Используйте команды или кнопки меню для навигации.\n\n"
                "Нажмите /start для главного меню или /help для помощи."
            )
    
    async def check_user_access(self, update: Update) -> bool:
        """Check if user has access (not banned, agreed to rules)"""
        user_id = str(update.effective_user.id)
        
        # Check if banned
        ban_info = await db.is_user_banned(user_id)
        if ban_info:
            message = ERROR_MESSAGES["banned"].format(
                reason=ban_info["reason"],
                until=ban_info["banned_until"].strftime("%d.%m.%Y %H:%M") if ban_info["banned_until"] else "навсегда"
            )
            if update.callback_query:
                await update.callback_query.answer(message, show_alert=True)
            else:
                await update.message.reply_text(message)
            return False
        
        # Check if agreed to rules
        user_data = await db.get_user(user_id)
        if not user_data or not user_data["agreed"]:
            message = ERROR_MESSAGES["not_agreed"]
            if update.callback_query:
                await update.callback_query.answer(message, show_alert=True)
            else:
                await update.message.reply_text(message)
            return False
        
        # Update activity
        await db.update_user_activity(user_id)
        return True
    
    # Admin Commands
    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot statistics (admin only)"""
        if not await self.check_admin(update):
            return
        
        stats = await db.get_stats()
        
        text = f"""
📊 <b>Статистика RUУчебник</b>

👥 Всего пользователей: {stats['total_users']}
📚 Всего учебников: {stats['total_textbooks']}
🟢 Активных сегодня: {stats['active_today']}
📥 Всего скачиваний: {stats['total_downloads']}
⚡ Запросов сегодня: {stats['requests_today']}

🕐 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
        
        await update.message.reply_text(text, parse_mode='HTML')
    
    async def admin_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent users (admin only)"""
        if not await self.check_admin(update):
            return
        
        # For simplicity, just show stats
        stats = await db.get_stats()
        await update.message.reply_text(
            f"👥 Всего пользователей в системе: {stats['total_users']}\n"
            f"🟢 Активных сегодня: {stats['active_today']}\n\n"
            f"Подробная информация доступна в веб-панели администратора."
        )
    
    async def admin_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start broadcast process (admin only)"""
        if not await self.check_admin(update):
            return
        
        context.user_data['waiting_for_broadcast'] = True
        await update.message.reply_text(
            "📢 Введите сообщение для рассылки всем пользователям:\n\n"
            "Отправьте /cancel для отмены."
        )
    
    async def handle_admin_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle broadcast message from admin"""
        if update.message.text == "/cancel":
            context.user_data.pop('waiting_for_broadcast', None)
            await update.message.reply_text("❌ Рассылка отменена.")
            return
        
        message = update.message.text
        user_ids = await db.get_all_user_ids()
        
        await update.message.reply_text(f"📤 Начинаю рассылку для {len(user_ids)} пользователей...")
        
        sent_count = 0
        failed_count = 0
        
        for user_id in user_ids:
            try:
                await context.bot.send_message(chat_id=user_id, text=message)
                sent_count += 1
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                failed_count += 1
                logger.warning(f"Failed to send broadcast to {user_id}: {e}")
        
        # Save broadcast record
        await db.save_broadcast(message, sent_count, str(update.effective_user.id))
        
        context.user_data.pop('waiting_for_broadcast', None)
        
        await update.message.reply_text(
            f"✅ Рассылка завершена!\n\n"
            f"📤 Отправлено: {sent_count}\n"
            f"❌ Ошибок: {failed_count}"
        )
    
    async def admin_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ban user command (admin only)"""
        if not await self.check_admin(update):
            return
        
        # Simple ban command format: /ban user_id reason days
        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "❌ Формат: /ban <user_id> <reason> [days]\n"
                    "Пример: /ban 123456789 Спам 30"
                )
                return
            
            user_id = args[0]
            reason = " ".join(args[1:-1]) if len(args) > 2 else args[1]
            days = None
            
            if len(args) > 2 and args[-1].isdigit():
                days = int(args[-1])
                reason = " ".join(args[1:-1])
            
            await db.ban_user(user_id, reason, days, str(update.effective_user.id))
            
            ban_text = f"✅ Пользователь {user_id} заблокирован"
            if days:
                ban_text += f" на {days} дней"
            ban_text += f"\nПричина: {reason}"
            
            await update.message.reply_text(ban_text)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
    
    async def admin_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Unban user command (admin only)"""
        if not await self.check_admin(update):
            return
        
        try:
            if not context.args:
                await update.message.reply_text("❌ Формат: /unban <user_id>")
                return
            
            user_id = context.args[0]
            success = await db.unban_user(user_id)
            
            if success:
                await update.message.reply_text(f"✅ Пользователь {user_id} разблокирован")
            else:
                await update.message.reply_text(f"❌ Пользователь {user_id} не найден в списке заблокированных")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
    
    async def admin_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent logs (admin only)"""
        if not await self.check_admin(update):
            return
        
        logs = await db.get_recent_logs(10)
        
        if not logs:
            await update.message.reply_text("📝 Логи пусты")
            return
        
        text = "📝 <b>Последние 10 записей логов:</b>\n\n"
        
        for log in logs:
            timestamp = log['timestamp'].strftime('%d.%m %H:%M')
            text += f"🕐 {timestamp} | {log['type']} | {log['action']}\n"
        
        text += f"\nПодробные логи доступны в веб-панели."
        
        await update.message.reply_text(text, parse_mode='HTML')
    
    async def check_admin(self, update: Update) -> bool:
        """Check if user is admin"""
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Доступ запрещен. Команда только для администратора.")
            return False
        return True
    
    async def run(self):
        """Run the bot"""
        try:
            await self.initialize()
            logger.info("Starting bot...")
            await self.application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Bot error: {e}")
            raise
        finally:
            await db.close()

# Main execution
async def main():
    bot = RUUchebnikBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
