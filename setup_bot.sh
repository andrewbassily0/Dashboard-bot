#!/bin/bash

echo "🚀 إعداد بوت قطع غيار السيارات..."

# التحقق من وجود Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker غير مثبت. يرجى تثبيت Docker أولاً."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose غير مثبت. يرجى تثبيت Docker Compose أولاً."
    exit 1
fi

echo "✅ Docker و Docker Compose مثبتان"

# إنشاء ملف .env إذا لم يكن موجوداً
if [ ! -f .env ]; then
    echo "📝 إنشاء ملف .env..."
    cat > .env << 'EOF'
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration
DATABASE_URL=postgresql://postgres:postgres123@db:5432/auto_parts_bot

# n8n Configuration
N8N_WEBHOOK_URL=http://n8n:5678
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=admin123

# Business Configuration
DEFAULT_COMMISSION_PERCENTAGE=2.0
DEFAULT_PAYMENT_URL=https://your-payment-gateway.com
REQUEST_EXPIRY_HOURS=6

# Admin Configuration
ADMIN_EMAIL=admin@example.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
EOF
    echo "✅ تم إنشاء ملف .env"
    echo "⚠️  يرجى تعديل TELEGRAM_BOT_TOKEN في ملف .env"
else
    echo "✅ ملف .env موجود بالفعل"
fi

# بناء وتشغيل المشروع
echo "🔨 بناء وتشغيل المشروع..."
docker-compose build
docker-compose up -d

# انتظار تشغيل الخدمات
echo "⏳ انتظار تشغيل الخدمات..."
sleep 15

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
echo "🎉 تم إعداد المشروع بنجاح!"
echo ""
echo "📱 للوصول للخدمات:"
echo "   - الداشبورد: http://localhost"
echo "   - Django Admin: http://localhost/admin/"
echo "   - n8n: http://localhost:5678 (admin/admin123)"
echo ""
echo "🤖 لتشغيل البوت:"
echo "   - للتطوير: docker-compose exec django_app python manage_bot.py polling"
echo "   - للإنتاج: docker-compose exec django_app python manage_bot.py webhook"
echo ""
echo "⚠️  تذكر تعديل TELEGRAM_BOT_TOKEN في ملف .env قبل تشغيل البوت!" 