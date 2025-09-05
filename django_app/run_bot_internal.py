#!/usr/bin/env python3
"""
Internal bot runner to avoid multiple instances
"""

import os
import sys
import threading
import time
import signal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_parts_bot.settings')

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from bot.telegram_bot import telegram_bot
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SingleBotRunner:
    def __init__(self):
        self.running = False
        
    def start_bot(self):
        """Start the bot in a controlled way"""
        if self.running:
            logger.warning("Bot is already running!")
            return
            
        try:
            logger.info("Setting up bot application...")
            application = telegram_bot.setup_bot()
            
            if not application:
                logger.error("Failed to setup bot application")
                return
                
            logger.info("Starting bot with polling...")
            self.running = True
            
            # Start polling (this blocks)
            application.run_polling(
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True
            )
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Error running bot: {e}")
        finally:
            self.running = False
            
    def stop_bot(self):
        """Stop the bot"""
        self.running = False

# Global bot runner
bot_runner = SingleBotRunner()

def signal_handler(signum, frame):
    logger.info("Received stop signal, shutting down...")
    bot_runner.stop_bot()
    sys.exit(0)

# Setup signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    logger.info("🚀 Starting Telegram Bot...")
    bot_runner.start_bot() 