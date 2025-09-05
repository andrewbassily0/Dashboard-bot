#!/usr/bin/env python3
"""
Fix Telegram Bot Issues
This script fixes common issues with the Telegram bot and restarts it properly.
"""

import os
import sys
import django
import asyncio
import logging
import signal
import time
import threading
from telegram.ext import Application

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_parts_bot.settings')
django.setup()

from django.conf import settings
from bot.telegram_bot import telegram_bot

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        self.application = None
        self.is_running = False
        self.polling_thread = None
        
    def setup_bot(self):
        """Setup the bot application with error handling"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN not found in settings")
            logger.info("💡 يرجى إضافة TELEGRAM_BOT_TOKEN في ملف .env")
            return None
        
        try:
            self.application = telegram_bot.setup_bot()
            if not self.application:
                logger.error("❌ Failed to setup bot application")
                return None
            
            logger.info("✅ Bot application setup successfully")
            return self.application
            
        except Exception as e:
            logger.error(f"❌ Error setting up bot: {e}")
            return None
    
    def start_polling_sync(self):
        """Start bot with polling in a separate thread to avoid event loop conflicts"""
        try:
            # Setup bot application
            application = self.setup_bot()
            if not application:
                return False
            
            self.is_running = True
            logger.info("🚀 Starting bot with polling...")
            
            # Create new event loop in separate thread
            def run_polling():
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Start polling
                    loop.run_until_complete(application.run_polling(
                        allowed_updates=['message', 'callback_query'],
                        drop_pending_updates=True,
                        close_loop=False
                    ))
                except Exception as e:
                    logger.error(f"❌ Error in polling thread: {e}")
                finally:
                    try:
                        loop.close()
                    except:
                        pass
            
            # Start polling in background thread
            self.polling_thread = threading.Thread(target=run_polling, daemon=True)
            self.polling_thread.start()
            
            logger.info("✅ Bot started successfully in background thread")
            logger.info("💡 البوت يعمل الآن! يمكنك إرسال /start على تليجرام")
            
            # Keep main thread alive
            try:
                while self.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                self.stop_bot()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in polling: {e}")
            return False
    
    def stop_bot(self):
        """Stop the bot gracefully"""
        if self.application and self.is_running:
            logger.info("🛑 Stopping bot...")
            self.is_running = False
            
            # Wait for polling thread to finish
            if self.polling_thread and self.polling_thread.is_alive():
                self.polling_thread.join(timeout=5)
            
            logger.info("✅ Bot stopped successfully")

def run_bot_simple():
    """Run bot in simple mode without complex threading"""
    try:
        # Check if bot token is set
        if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == 'your_telegram_bot_token_here':
            logger.error("❌ TELEGRAM_BOT_TOKEN not set properly")
            logger.info("💡 يرجى تعديل ملف .env وإضافة token صحيح")
            logger.info("📝 مثال: TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
            return
        
        # Setup bot application
        application = telegram_bot.setup_bot()
        if not application:
            logger.error("❌ Failed to setup bot application")
            return
        
        logger.info("✅ Bot application setup successfully")
        logger.info("🚀 Starting bot with polling...")
        
        # Use a simple approach - just start the application
        # This will work better with Django's event loop
        try:
            # Start the application in the current thread
            application.run_polling(
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True,
                close_loop=False
            )
        except Exception as e:
            logger.error(f"❌ Error in polling: {e}")
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")

async def main():
    """Main function to run the bot"""
    bot_manager = BotManager()
    
    try:
        # Check if bot token is set
        if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == 'your_telegram_bot_token_here':
            logger.error("❌ TELEGRAM_BOT_TOKEN not set properly")
            logger.info("💡 يرجى تعديل ملف .env وإضافة token صحيح")
            logger.info("📝 مثال: TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
            return
        
        # Start the bot
        await bot_manager.start_polling()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        await bot_manager.stop_bot()

if __name__ == "__main__":
    try:
        # Use simple mode to avoid event loop conflicts
        run_bot_simple()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1) 