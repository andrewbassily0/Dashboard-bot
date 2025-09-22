#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
حل جذري نهائي لمشكلة تضارب البوت
يستخدم webhook mode بدلاً من polling نهائياً
"""

import requests
import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'إعداد البوت في webhook mode - حل جذري لمشكلة التضارب'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            type=str,
            default='localhost:8888',
            help='Domain للـ webhook (default: localhost:8888)'
        )
        parser.add_argument(
            '--ssl',
            action='store_true',
            help='استخدام HTTPS (production)'
        )
        parser.add_argument(
            '--delete-webhook',
            action='store_true',
            help='حذف الـ webhook الحالي'
        )

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        domain = options['domain']
        use_ssl = options['ssl']
        delete_webhook = options['delete_webhook']
        
        if not token:
            self.stdout.write(self.style.ERROR('❌ TELEGRAM_BOT_TOKEN غير موجود'))
            return

        self.stdout.write(self.style.SUCCESS('🔧 بدء إعداد البوت الجذري...'))

        # حذف الـ webhook إذا طلب
        if delete_webhook:
            self.delete_webhook(token)
            return

        # إعداد webhook جديد
        self.setup_webhook(token, domain, use_ssl)

    def delete_webhook(self, token):
        """حذف الـ webhook الحالي نهائياً"""
        self.stdout.write('🗑️ حذف الـ webhook الحالي...')
        
        delete_url = f'https://api.telegram.org/bot{token}/deleteWebhook'
        params = {'drop_pending_updates': True}
        
        response = requests.get(delete_url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                self.stdout.write(self.style.SUCCESS('✅ تم حذف الـ webhook بنجاح!'))
                self.stdout.write('🔄 البوت جاهز الآن للـ webhook الجديد')
            else:
                self.stdout.write(self.style.ERROR(f'❌ فشل حذف الـ webhook: {result.get("description")}'))
        else:
            self.stdout.write(self.style.ERROR('❌ خطأ في الاتصال بـ Telegram API'))

    def setup_webhook(self, token, domain, use_ssl):
        """إعداد webhook جديد"""
        # تحديد URL الصحيح
        protocol = 'https' if use_ssl else 'http'
        webhook_url = f'{protocol}://{domain}/bot/webhook/telegram/'
        
        self.stdout.write(f'🌐 إعداد webhook على: {webhook_url}')

        # حذف أي webhook سابق أولاً
        self.stdout.write('🧹 تنظيف الـ webhooks السابقة...')
        delete_url = f'https://api.telegram.org/bot{token}/deleteWebhook'
        requests.get(delete_url, params={'drop_pending_updates': True})

        # تعيين webhook جديد
        self.stdout.write('📡 تعيين webhook جديد...')
        set_url = f'https://api.telegram.org/bot{token}/setWebhook'
        
        data = {
            'url': webhook_url,
            'drop_pending_updates': True,
            'allowed_updates': ['message', 'callback_query']
        }
        
        response = requests.post(set_url, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                self.stdout.write(self.style.SUCCESS('✅ تم إعداد الـ webhook بنجاح!'))
                
                # التحقق من حالة الـ webhook
                self.check_webhook_status(token)
                
                self.stdout.write(self.style.SUCCESS('🎉 البوت يعمل الآن في webhook mode!'))
                self.stdout.write('📱 جرب إرسال رسالة للبوت للتأكد من عمله')
                
            else:
                self.stdout.write(self.style.ERROR(f'❌ فشل إعداد الـ webhook: {result.get("description")}'))
        else:
            self.stdout.write(self.style.ERROR('❌ خطأ في الاتصال بـ Telegram API'))

    def check_webhook_status(self, token):
        """فحص حالة الـ webhook"""
        self.stdout.write('🔍 فحص حالة الـ webhook...')
        
        info_url = f'https://api.telegram.org/bot{token}/getWebhookInfo'
        response = requests.get(info_url)
        
        if response.status_code == 200:
            webhook_info = response.json()['result']
            
            self.stdout.write(f'📊 معلومات الـ webhook:')
            self.stdout.write(f'   URL: {webhook_info.get("url", "غير محدد")}')
            self.stdout.write(f'   Updates عالقة: {webhook_info.get("pending_update_count", 0)}')
            self.stdout.write(f'   آخر خطأ: {webhook_info.get("last_error_message", "لا يوجد")}')
            
            if webhook_info.get('url'):
                self.stdout.write(self.style.SUCCESS('✅ الـ webhook مفعل ويعمل!'))
            else:
                self.stdout.write(self.style.WARNING('⚠️ الـ webhook غير مفعل'))
        else:
            self.stdout.write(self.style.ERROR('❌ فشل فحص حالة الـ webhook'))
