#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 حل جذري نهائي لمشكلة تضارب البوت
يدير البوت في webhook mode بدلاً من polling
"""

import os
import sys
import django
import subprocess
import requests
import time

# إعداد Django
sys.path.append('/project/Dashboard-bot/django_app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_parts_bot.settings')
django.setup()

from django.conf import settings


class BotWebhookManager:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.domain = 'localhost:8888'  # يمكن تغييره للـ production
        
    def clear_all_bot_processes(self):
        """إيقاف جميع عمليات البوت العالقة"""
        print('🧹 تنظيف جميع عمليات البوت العالقة...')
        
        # تنظيف webhook
        if self.token:
            delete_url = f'https://api.telegram.org/bot{self.token}/deleteWebhook'
            params = {'drop_pending_updates': True}
            
            try:
                response = requests.get(delete_url, params=params, timeout=10)
                if response.status_code == 200:
                    print('✅ تم تنظيف الـ webhook')
                else:
                    print('⚠️ فشل تنظيف الـ webhook')
            except Exception as e:
                print(f'⚠️ خطأ في تنظيف الـ webhook: {e}')
        
        print('✅ تم تنظيف عمليات البوت')

    def setup_webhook(self):
        """إعداد webhook للبوت"""
        if not self.token:
            print('❌ TELEGRAM_BOT_TOKEN غير موجود')
            return False
            
        webhook_url = f'http://{self.domain}/bot/webhook/telegram/'
        print(f'📡 إعداد webhook على: {webhook_url}')
        
        set_url = f'https://api.telegram.org/bot{self.token}/setWebhook'
        data = {
            'url': webhook_url,
            'drop_pending_updates': True,
            'allowed_updates': ['message', 'callback_query']
        }
        
        try:
            response = requests.post(set_url, data=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    print('✅ تم إعداد الـ webhook بنجاح!')
                    return True
                else:
                    print(f'❌ فشل إعداد الـ webhook: {result.get("description")}')
            else:
                print(f'❌ خطأ HTTP: {response.status_code}')
        except Exception as e:
            print(f'❌ خطأ في إعداد الـ webhook: {e}')
        
        return False

    def check_webhook_status(self):
        """فحص حالة الـ webhook"""
        print('🔍 فحص حالة الـ webhook...')
        
        info_url = f'https://api.telegram.org/bot{self.token}/getWebhookInfo'
        
        try:
            response = requests.get(info_url, timeout=10)
            if response.status_code == 200:
                webhook_info = response.json()['result']
                
                print(f'📊 معلومات الـ webhook:')
                print(f'   URL: {webhook_info.get("url", "غير محدد")}')
                print(f'   Updates عالقة: {webhook_info.get("pending_update_count", 0)}')
                
                last_error = webhook_info.get("last_error_message")
                if last_error:
                    print(f'   آخر خطأ: {last_error}')
                else:
                    print('   ✅ لا توجد أخطاء')
                
                return webhook_info.get('url') is not None
            else:
                print(f'❌ خطأ في فحص الـ webhook: {response.status_code}')
        except Exception as e:
            print(f'❌ خطأ في فحص الـ webhook: {e}')
        
        return False

    def start_django_server(self):
        """تشغيل Django server"""
        print('🚀 تشغيل Django server...')
        
        try:
            # إيقاف أي server عامل
            subprocess.run(['pkill', '-f', 'manage.py'], capture_output=True)
            time.sleep(2)
            
            # تشغيل server جديد
            cmd = [
                'python', 
                '/project/Dashboard-bot/django_app/manage.py', 
                'runserver', 
                '0.0.0.0:8000'
            ]
            
            print('📡 Django server بدأ على المنفذ 8000')
            return subprocess.Popen(cmd, cwd='/project/Dashboard-bot/django_app')
            
        except Exception as e:
            print(f'❌ خطأ في تشغيل Django server: {e}')
            return None

    def run_complete_setup(self):
        """إعداد شامل للبوت"""
        print('🔧 بدء الإعداد الشامل للبوت...')
        print('='*50)
        
        # 1. تنظيف العمليات
        self.clear_all_bot_processes()
        
        # 2. تشغيل Django
        server_process = self.start_django_server()
        if not server_process:
            print('❌ فشل تشغيل Django server')
            return False
        
        # 3. انتظار حتى يبدأ الـ server
        print('⏳ انتظار Django server...')
        time.sleep(5)
        
        # 4. إعداد webhook
        if not self.setup_webhook():
            print('❌ فشل إعداد الـ webhook')
            server_process.terminate()
            return False
        
        # 5. فحص النتائج
        if self.check_webhook_status():
            print('='*50)
            print('🎉 تم إعداد البوت بنجاح!')
            print('📱 البوت يعمل الآن في webhook mode')
            print('🔗 اختبر البوت على: @tashaleeh_bot')
            print('='*50)
            
            # إبقاء الـ server يعمل
            try:
                print('🔄 الـ server يعمل... اضغط Ctrl+C للإيقاف')
                server_process.wait()
            except KeyboardInterrupt:
                print('\n🛑 إيقاف الـ server...')
                server_process.terminate()
                
            return True
        else:
            print('❌ فشل في التحقق من الـ webhook')
            server_process.terminate()
            return False


if __name__ == '__main__':
    manager = BotWebhookManager()
    success = manager.run_complete_setup()
    
    if success:
        print('✅ العملية اكتملت بنجاح!')
    else:
        print('❌ فشلت العملية')
    
    exit(0 if success else 1)
