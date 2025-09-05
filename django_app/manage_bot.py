#!/usr/bin/env python3
"""
Telegram Bot Management Script
This script handles the Telegram bot operations including webhook setup and polling.
"""

import os
import sys
import django
import asyncio
import logging
import threading
import time
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

async def setup_webhook():
    """Setup webhook for the bot"""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in settings")
        return False
    
    webhook_url = getattr(settings, 'TELEGRAM_WEBHOOK_URL', '')
    if not webhook_url:
        logger.error("TELEGRAM_WEBHOOK_URL not found in settings")
        return False
    
    try:
        # Setup bot application
        application = telegram_bot.setup_bot()
        if not application:
            logger.error("Failed to setup bot application")
            return False
        
        # Set webhook
        await application.bot.set_webhook(
            url=webhook_url,
            allowed_updates=['message', 'callback_query', 'inline_query']
        )
        
        logger.info(f"Webhook set successfully: {webhook_url}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up webhook: {e}")
        return False

async def remove_webhook():
    """Remove webhook and use polling instead"""
    try:
        application = telegram_bot.setup_bot()
        if not application:
            logger.error("Failed to setup bot application")
            return False
        
        await application.bot.delete_webhook()
        logger.info("Webhook removed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error removing webhook: {e}")
        return False

def start_polling_simple():
    """Start bot with polling in simple mode to avoid event loop conflicts"""
    try:
        # Setup bot application
        application = telegram_bot.setup_bot()
        if not application:
            logger.error("Failed to setup bot application")
            return False
        
        logger.info("Starting bot with polling...")
        
        # Use simple approach - just start the application
        # This will work better with Django's event loop
        try:
            # Start the application in the current thread
            application.run_polling(
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True,
                close_loop=False
            )
        except Exception as e:
            logger.error(f"Error in polling: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in polling: {e}")
        return False

def start_polling_sync():
    """Start bot with polling in a separate thread to avoid event loop conflicts"""
    try:
        # Setup bot application
        application = telegram_bot.setup_bot()
        if not application:
            logger.error("Failed to setup bot application")
            return False
        
        logger.info("Starting bot with polling...")
        
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
                logger.error(f"Error in polling thread: {e}")
            finally:
                try:
                    loop.close()
                except:
                    pass
        
        # Start polling in background thread
        polling_thread = threading.Thread(target=run_polling, daemon=True)
        polling_thread.start()
        
        logger.info("Bot started successfully in background thread")
        logger.info("البوت يعمل الآن! يمكنك إرسال /start على تليجرام")
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in polling: {e}")
        return False

async def start_polling():
    """Start bot with polling (for development)"""
    try:
        # Setup bot application
        application = telegram_bot.setup_bot()
        if not application:
            logger.error("Failed to setup bot application")
            return
        
        logger.info("Starting bot with polling...")
        
        # Start polling
        await application.initialize()
        await application.start()
        await application.run_polling(allowed_updates=['message', 'callback_query'])
        
    except Exception as e:
        logger.error(f"Error in polling: {e}")
    finally:
        try:
            await application.stop()
            await application.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down application: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_bot.py [webhook|polling|remove_webhook]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "webhook":
            asyncio.run(setup_webhook())
        elif command == "polling":
            # Use simple mode to avoid event loop conflicts
            start_polling_simple()
        elif command == "remove_webhook":
            asyncio.run(remove_webhook())
        else:
            print("Invalid command. Use: webhook, polling, or remove_webhook")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

