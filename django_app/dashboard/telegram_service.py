import asyncio
import logging
import requests
from django.conf import settings
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class TelegramService:
    """Service for sending Telegram messages from dashboard"""
    
    def __init__(self):
        self.bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message_sync(self, chat_id: int, text: str, parse_mode: str = None) -> Dict[str, Any]:
        """Send message synchronously using requests"""
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not configured")
            return {"success": False, "error": "Bot token not configured"}
        
        url = f"{self.base_url}/sendMessage"
        
        data = {
            "chat_id": chat_id,
            "text": text
        }
        
        if parse_mode:
            data["parse_mode"] = parse_mode
        
        try:
            response = requests.post(url, json=data, timeout=10)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("ok"):
                logger.info(f"Message sent successfully to {chat_id}")
                return {"success": True, "data": response_data}
            else:
                error_msg = response_data.get("description", "Unknown error")
                logger.error(f"Failed to send message to {chat_id}: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except requests.RequestException as e:
            logger.error(f"Request error sending message to {chat_id}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error sending message to {chat_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def send_unban_notification(self, user) -> Dict[str, Any]:
        """Send unban notification to user"""
        if not user.telegram_id:
            return {"success": False, "error": "User has no telegram_id"}
        
        # Get user greeting (prefer first name, fallback to username)
        user_greeting = user.first_name if user.first_name else user.username
        
        # Unban message
        unban_message = f"""
🎉 تم فك الحظر من حسابك!

✅ أهلاً بك في تشاليح، {user_greeting}!

🔓 تم إلغاء الحظر من حسابك بنجاح ويمكنك الآن استخدام جميع خدمات البوت.

🚗 يمكنك الآن:
• طلب قطع الغيار التي تحتاجها
• تصفح العروض المتاحة
• التواصل مع أفضل المخازن في منطقتك

🌟 نرحب بك مرة أخرى ونتمنى لك تجربة ممتازة!

للبدء، أرسل /start
        """
        
        result = self.send_message_sync(user.telegram_id, unban_message)
        
        if result["success"]:
            logger.info(f"Unban notification sent to user {user.telegram_id} ({user.first_name})")
        else:
            logger.warning(f"Failed to send unban notification to user {user.telegram_id}: {result.get('error')}")
        
        return result
    
    def send_welcome_back_message(self, user) -> Dict[str, Any]:
        """Send a simple welcome back message"""
        if not user.telegram_id:
            return {"success": False, "error": "User has no telegram_id"}
        
        user_greeting = user.first_name if user.first_name else user.username
        
        message = f"""
🌟 مرحباً بك مرة أخرى، {user_greeting}!

تم تفعيل حسابك بنجاح. يمكنك الآن استخدام البوت.

أرسل /start للبدء 🚀
        """
        
        return self.send_message_sync(user.telegram_id, message)

# Global instance
telegram_service = TelegramService()
