# دليل البدء السريع - Auto Parts Bot

## التشغيل السريع (5 دقائق)

### 1. المتطلبات الأساسية
```bash
# تأكد من وجود Docker
docker --version

# تأكد من وجود Docker Compose
docker-compose --version
```

### 2. إعداد المتغيرات البيئية
```bash
# نسخ ملف المتغيرات
cp .env.example .env

# تحرير الملف (الحد الأدنى المطلوب)
nano .env
```

**أهم المتغيرات المطلوبة:**
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
DJANGO_SECRET_KEY=your-secret-key-here
```

### 3. تشغيل المشروع
```bash
# بناء وتشغيل جميع الخدمات
docker-compose up -d

# مراقبة السجلات
docker-compose logs -f
```

### 4. إعداد قاعدة البيانات
```bash
# تشغيل migrations
docker-compose exec django_app python manage.py migrate

# إنشاء superuser
docker-compose exec django_app python manage.py createsuperuser

# ملء البيانات الأساسية
docker-compose exec django_app python manage.py populate_data
```

### 5. الوصول للخدمات
- **الداشبورد**: http://localhost
- **Django Admin**: http://localhost/admin/
- **n8n**: http://localhost:5678 (admin/admin123)

### 6. إعداد البوت
```bash
# للتطوير (polling)
docker-compose exec django_app python manage_bot.py polling

# للإنتاج (webhook) - يتطلب domain
docker-compose exec django_app python manage_bot.py webhook
```

## الخدمات المتاحة

| الخدمة | المنفذ | الوصول |
|--------|--------|---------|
| Django App | 8000 | http://localhost:8000 |
| Nginx | 80 | http://localhost |
| PostgreSQL | 5432 | localhost:5432 |
| n8n | 5678 | http://localhost:5678 |

## أوامر مفيدة

```bash
# إيقاف الخدمات
docker-compose down

# إعادة بناء الخدمات
docker-compose build --no-cache

# مراقبة استخدام الموارد
docker stats

# دخول إلى حاوية Django
docker-compose exec django_app bash

# عرض السجلات
docker-compose logs django_app

# نسخ احتياطي لقاعدة البيانات
docker-compose exec db pg_dump -U postgres auto_parts_bot > backup.sql
```

## استكشاف الأخطاء السريع

### البوت لا يعمل؟
1. تأكد من صحة `TELEGRAM_BOT_TOKEN`
2. تحقق من السجلات: `docker-compose logs django_app`

### قاعدة البيانات لا تعمل؟
1. تأكد من تشغيل الحاوية: `docker-compose ps`
2. تحقق من السجلات: `docker-compose logs db`

### الموقع لا يفتح؟
1. تأكد من تشغيل nginx: `docker-compose ps`
2. تحقق من المنافذ: `netstat -tlnp | grep :80`

## الخطوات التالية

1. **إعداد البوت**: احصل على Bot Token من @BotFather
2. **إعداد n8n**: قم بإنشاء workflows للأتمتة
3. **تخصيص الإعدادات**: من لوحة التحكم الإدارية
4. **إضافة البيانات**: مدن، ماركات، موديلات جديدة
5. **اختبار النظام**: قم بإنشاء طلبات تجريبية

## الدعم الفني

للحصول على المساعدة:
1. راجع ملف `README.md` للتفاصيل الكاملة
2. راجع ملف `DEPLOYMENT.md` للنشر في الإنتاج
3. تحقق من السجلات للأخطاء التفصيلية

