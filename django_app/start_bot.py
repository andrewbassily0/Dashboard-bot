#!/usr/bin/env python3
import os
import sys
import django
import asyncio
import logging

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_parts_bot.settings')
django.setup()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    print("🚀 بدء تشغيل بوت قطع غيار السيارات...")
    print("=" * 60)
    
    try:
        from bot.telegram_bot import TelegramBot
        
        async def run():
            bot = TelegramBot()
            logger.info("✅ تم إنشاء البوت بنجاح")
            
            # Setup bot application
            app = bot.setup_bot()
            if not app:
                logger.error("❌ فشل في إعداد البوت")
                return
            
            logger.info("🔄 جاري بدء Polling...")
            
            try:
                await app.run_polling()
            except Exception as e:
                logger.error(f"❌ خطأ في Polling: {e}")
                raise
        
        # Run the bot
        asyncio.run(run())
        
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 