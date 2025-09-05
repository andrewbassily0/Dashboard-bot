#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Management command to run Telegram Bot
Supports both polling (development) and webhook (production) modes
"""

import asyncio
import signal
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from bot.telegram_bot import TelegramBot
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Telegram Bot - supports polling and webhook modes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            choices=['polling', 'webhook'],
            default='polling',
            help='Bot running mode: polling (development) or webhook (production)'
        )
        parser.add_argument(
            '--webhook-url',
            type=str,
            help='Webhook URL for production mode (e.g., https://yourdomain.com/bot/webhook/telegram/)'
        )

    def handle(self, *args, **options):
        mode = options['mode']
        webhook_url = options.get('webhook_url')
        
        self.stdout.write(f"Starting Telegram Bot in {mode} mode...")
        
        if mode == 'webhook' and not webhook_url:
            self.stdout.write(
                self.style.ERROR('Webhook URL is required for webhook mode. Use --webhook-url argument.')
            )
            return
        
        try:
            if mode == 'polling':
                asyncio.run(self.run_polling())
            else:
                asyncio.run(self.setup_webhook(webhook_url))
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Bot stopped by user.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Bot error: {e}'))

    async def run_polling(self):
        """Run bot in polling mode (for development)"""
        self.stdout.write("🚀 Starting bot in polling mode...")
        self.stdout.write("Press Ctrl+C to stop the bot")
        
        bot = TelegramBot()
        app = bot.setup_bot()
        
        if not app:
            self.stdout.write(self.style.ERROR('Failed to setup bot!'))
            return
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        
        def signal_handler():
            self.stdout.write(self.style.WARNING('\nReceived stop signal. Shutting down...'))
            for task in asyncio.all_tasks(loop):
                task.cancel()
        
        for sig in [signal.SIGTERM, signal.SIGINT]:
            loop.add_signal_handler(sig, signal_handler)
        
        try:
            await app.initialize()
            await app.start()
            
            self.stdout.write(self.style.SUCCESS('✅ Bot started successfully in polling mode!'))
            self.stdout.write('🔄 Listening for messages...')
            
            # Start polling
            await app.updater.start_polling(
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True
            )
            
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Polling error: {e}'))
        finally:
            self.stdout.write('🛑 Stopping bot...')
            try:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
                self.stdout.write(self.style.SUCCESS('✅ Bot stopped successfully.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error during shutdown: {e}'))

    async def setup_webhook(self, webhook_url):
        """Setup webhook for production mode"""
        import requests
        
        bot_token = settings.TELEGRAM_BOT_TOKEN
        telegram_api_url = f"https://api.telegram.org/bot{bot_token}"
        
        self.stdout.write(f"🌐 Setting up webhook: {webhook_url}")
        
        # Delete existing webhook
        delete_response = requests.get(f"{telegram_api_url}/deleteWebhook")
        if delete_response.json().get('ok'):
            self.stdout.write(self.style.SUCCESS('✅ Existing webhook deleted'))
        
        # Set new webhook
        webhook_data = {
            'url': webhook_url,
            'allowed_updates': ['message', 'callback_query'],
            'drop_pending_updates': True
        }
        
        set_response = requests.post(f"{telegram_api_url}/setWebhook", json=webhook_data)
        result = set_response.json()
        
        if result.get('ok'):
            self.stdout.write(self.style.SUCCESS(f'✅ Webhook set successfully: {webhook_url}'))
            self.stdout.write('🎯 Bot is now ready to receive updates via webhook!')
            
            # Verify webhook
            info_response = requests.get(f"{telegram_api_url}/getWebhookInfo")
            info_result = info_response.json()
            
            if info_result.get('ok'):
                webhook_info = info_result['result']
                self.stdout.write('📊 Webhook Info:')
                self.stdout.write(f"   URL: {webhook_info.get('url')}")
                self.stdout.write(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")
                self.stdout.write(f"   Allowed updates: {webhook_info.get('allowed_updates', [])}")
        else:
            self.stdout.write(self.style.ERROR(f'❌ Failed to set webhook: {result.get("description", "Unknown error")}'))
