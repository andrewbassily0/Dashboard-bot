#!/usr/bin/env python
"""
Simple script to run the Telegram bot
"""
import os
import sys
import django
import logging

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_parts_bot.settings')
django.setup()

from bot.telegram_bot import TelegramBot

# Setup logging with Unicode support - remove emojis to avoid encoding issues


class SafeFormatter(logging.Formatter):
    def format(self, record):
        # Remove or replace problematic Unicode characters
        msg = super().format(record)
        # Replace common emoji characters that cause issues
        emoji_replacements = {
            '🚀': '[START]',
            '🔄': '[PROCESSING]',
            '📝': '[UPDATE]',
            '📢': '[NOTIFY]',
            '📊': '[INFO]',
            '✅': '[SUCCESS]',
            '❌': '[ERROR]',
            '📡': '[POLLING]',
            '🛒': '[ORDER]',
            '🔧': '[TOOL]',
            '🎯': '[TARGET]',
            '🏠': '[HOME]',
            '📋': '[LIST]',
            '🆕': '[NEW]',
        }
        for emoji, replacement in emoji_replacements.items():
            msg = msg.replace(emoji, replacement)
        return msg

# Setup logging


handler = logging.StreamHandler()
format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
formatter = SafeFormatter(format_str)
handler.setFormatter(formatter)
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run the bot"""
    try:
        logger.info("🚀 Starting Telegram Bot...")

        # Create bot instance
        bot = TelegramBot()

        # Setup bot application
        application = bot.setup_bot()
        if not application:
            logger.error("❌ Failed to setup bot application")
            return

        logger.info("✅ Bot application setup successfully")
        logger.info("📡 Starting polling...")

        # Start polling (this will handle the event loop internally)
        application.run_polling(
            allowed_updates=['message', 'callback_query'],
            drop_pending_updates=True
        )

    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
