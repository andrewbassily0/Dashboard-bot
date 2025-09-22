#!/usr/bin/env python3
"""
Database Utilities for Telegram Bot - حل مشكلة انقطاع الاتصال

هذا الملف يحتوي على utilities لحل مشكلة انقطاع اتصال قاعدة البيانات
في البيئة غير المتزامنة (async) للبوت.
"""

import logging
from functools import wraps
from django.db import connection
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

def ensure_db_connection(func):
    """
    Decorator لضمان اتصال قاعدة البيانات قبل تنفيذ العملية
    
    يستخدم مع الدوال المزامنة (sync) قبل تحويلها إلى async
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # إغلاق الاتصال الحالي لإجبار إعادة الاتصال
        try:
            connection.close()
        except Exception:
            pass
        
        # محاولة تنفيذ العملية
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # إذا فشلت، جرب مرة أخرى بعد إعادة الاتصال
            logger.warning(f"Database operation failed, retrying: {e}")
            try:
                connection.close()
                return func(*args, **kwargs)
            except Exception as retry_error:
                logger.error(f"Database operation failed after retry: {retry_error}")
                raise
    
    return wrapper

def safe_sync_to_async(func):
    """
    Wrapper آمن لـ sync_to_async يتعامل مع مشاكل قاعدة البيانات
    """
    return sync_to_async(ensure_db_connection(func))

def test_db_connection():
    """
    اختبار اتصال قاعدة البيانات
    """
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

async def ensure_async_db_connection():
    """
    التأكد من اتصال قاعدة البيانات في البيئة غير المتزامنة
    """
    return await sync_to_async(test_db_connection)()

def get_db_stats():
    """
    الحصول على إحصائيات قاعدة البيانات
    """
    try:
        from bot.models import User, Request, Offer, Junkyard
        
        stats = {
            'users': User.objects.count(),
            'requests': Request.objects.count(), 
            'offers': Offer.objects.count(),
            'junkyards': Junkyard.objects.count(),
            'connection_status': test_db_connection()
        }
        
        return stats
    except Exception as e:
        logger.error(f"Error getting DB stats: {e}")
        return {'error': str(e), 'connection_status': False}

# مثال على الاستخدام:
"""
# بدلاً من:
@sync_to_async
def get_user(telegram_id):
    return User.objects.get(telegram_id=telegram_id)

# استخدم:
@safe_sync_to_async
def get_user(telegram_id):
    return User.objects.get(telegram_id=telegram_id)
"""
