from django.core.management.base import BaseCommand
import logging
import signal
import sys
from bot.telegram_bot import telegram_bot

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run Telegram Bot with single instance protection'
    
    def __init__(self):
        super().__init__()
        self.bot_running = False
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force start even if another instance might be running',
        )
    
    def handle_shutdown(self, signum, frame):
        self.stdout.write(self.style.WARNING("Received shutdown signal, stopping bot..."))
        self.bot_running = False
        sys.exit(0)
    
    def handle(self, *args, **options):
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        try:
            self.stdout.write(self.style.SUCCESS("🚀 Starting Telegram Bot..."))
            
            # Setup bot application
            application = telegram_bot.setup_bot()
            if not application:
                self.stdout.write(self.style.ERROR("Failed to setup bot application"))
                return
            
            self.stdout.write(self.style.SUCCESS("✅ Bot application setup successfully"))
            self.stdout.write(self.style.SUCCESS("📡 Starting polling..."))
            
            self.bot_running = True
            
            # Start polling (this blocks)
            application.run_polling(
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True
            )
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Bot stopped by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error running bot: {e}"))
            logger.error(f"Bot error: {e}")
        finally:
            self.bot_running = False
            self.stdout.write(self.style.SUCCESS("🛑 Bot stopped")) 