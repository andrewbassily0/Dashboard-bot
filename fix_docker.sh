#!/bin/bash

echo "🔧 إصلاح مشاكل Docker..."

# إيقاف جميع الحاويات
echo "🛑 إيقاف جميع الحاويات..."
docker-compose down -v

# تنظيف Docker
echo "🧹 تنظيف Docker..."
docker system prune -f
docker volume prune -f
docker network prune -f

# حذف الصور القديمة
echo "🗑️  حذف الصور القديمة..."
docker rmi $(docker images -q) 2>/dev/null || true

# إعادة بناء المشروع
echo "🔨 إعادة بناء المشروع..."
docker-compose build --no-cache

# تشغيل المشروع
echo "🚀 تشغيل المشروع..."
docker-compose up -d

# انتظار تشغيل الخدمات
echo "⏳ انتظار تشغيل الخدمات..."
sleep 20

# فحص حالة الخدمات
echo "📊 فحص حالة الخدمات..."
docker-compose ps

# إعداد قاعدة البيانات
echo "🗄️  إعداد قاعدة البيانات..."
docker-compose exec -T django_app python manage.py migrate
docker-compose exec -T django_app python manage.py collectstatic --noinput

# إنشاء superuser
echo "👤 إنشاء superuser..."
docker-compose exec -T django_app python manage.py createsuperuser --noinput --username admin --email admin@example.com || true

# ملء البيانات الأساسية
echo "📊 ملء البيانات الأساسية..."
docker-compose exec -T django_app python manage.py populate_data

echo ""
echo "🎉 تم إصلاح المشروع بنجاح!"
echo ""
echo "📱 للوصول للخدمات:"
echo "   - الداشبورد: http://localhost"
echo "   - Django Admin: http://localhost/admin/"
echo "   - n8n: http://localhost:5678 (admin/admin123)"
echo ""
echo "🤖 لتشغيل البوت:"
echo "   - للتطوير: docker-compose exec django_app python fix_bot.py"
echo ""
echo "⚠️  تذكر تعديل TELEGRAM_BOT_TOKEN في ملف .env قبل تشغيل البوت!" 