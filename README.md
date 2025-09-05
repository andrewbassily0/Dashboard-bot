# 🚗 تشاليح - منصة قطع غيار السيارات

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Django](https://img.shields.io/badge/django-4.2-green.svg)

## 📋 وصف المشروع

تشاليح هو نظام متكامل لإدارة طلبات قطع غيار السيارات يتكون من:

- 🤖 **Telegram Bot** للعملاء لطلب قطع الغيار
- 📊 **Dashboard** لإدارة الطلبات والتشاليح والمستخدمين
- 🔄 **API** للتكامل مع الأنظمة الخارجية

## ✨ المميزات

### 🤖 Telegram Bot
- واجهة عربية سهلة الاستخدام
- إدارة طلبات متعددة لكل مستخدم
- نظام العروض والقبول/الرفض
- تقييم الخدمة
- حماية من المستخدمين المحظورين

### 📊 Dashboard
- تصميم glassmorphism عصري
- إدارة المستخدمين والتشاليح
- إحصائيات شاملة ومتقدمة
- نظام إدارة الطلبات والعروض
- واجهة إدارة Django محسنة

### 🛡️ الأمان
- نظام مصادقة Django كامل
- حماية CSRF
- إدارة الصلاحيات
- تشفير البيانات الحساسة

## 🛠️ التقنيات المستخدمة

- **Backend**: Django 4.2, Python 3.11
- **Database**: PostgreSQL
- **Cache**: Redis
- **Bot**: python-telegram-bot
- **Frontend**: HTML5, TailwindCSS, Alpine.js
- **Deployment**: Docker, Nginx
- **Automation**: n8n

## 🚀 التشغيل

### متطلبات النظام
- Docker & Docker Compose
- Python 3.11+
- PostgreSQL
- Redis

### خطوات التشغيل

1. **استنساخ المشروع**
```bash
git clone <repository-url>
cd auto-bot
```

2. **إعداد متغيرات البيئة**
```bash
cp .env.example .env
# تحديث .env بالبيانات المطلوبة
```

3. **تشغيل المشروع**
```bash
docker-compose up -d
```

4. **تطبيق migrations**
```bash
docker exec auto-bot-django_app-1 python manage.py migrate
```

5. **إنشاء superuser**
```bash
docker exec auto-bot-django_app-1 python manage.py createsuperuser
```

6. **إضافة البيانات التجريبية**
```bash
docker exec auto-bot-django_app-1 python manage.py populate_data
```

## 🔧 إعداد البوت

### Development (Polling)
```bash
docker exec auto-bot-django_app-1 python manage.py run_bot --mode=polling
```

### Production (Webhook)
```bash
docker exec auto-bot-django_app-1 python manage.py run_bot --mode=webhook --webhook-url=https://yourdomain.com/bot/webhook/telegram/
```

## 📁 هيكل المشروع

```
auto-bot/
├── django_app/
│   ├── bot/                 # تطبيق البوت والنماذج
│   ├── dashboard/           # تطبيق الداشبورد
│   ├── templates/           # قوالب HTML
│   ├── static/             # الملفات الثابتة
│   └── auto_parts_bot/     # إعدادات Django
├── docker-compose.yml      # إعدادات Docker
├── nginx/                  # إعدادات Nginx
├── n8n/                   # إعدادات n8n
└── README.md
```

## 🌐 المتغيرات البيئية

```env
# Django
DEBUG=False
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=auto_parts_bot
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=db
DB_PORT=5432

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token

# Redis
REDIS_URL=redis://redis:6379/1
```

## 📊 API Endpoints

### Bot Webhook
- `POST /bot/webhook/telegram/` - Telegram webhook

### Dashboard API
- `GET /dashboard/api/stats/` - إحصائيات النظام
- `GET /health/` - فحص صحة النظام

### n8n Integration
- `POST /bot/api/junkyards/` - قائمة التشاليح
- `GET /bot/webhook/n8n/new-request/` - طلبات جديدة
- `POST /bot/webhook/n8n/new-offer/` - عروض جديدة

## 🔍 المراقبة

### مراقبة اللوجز
```bash
# Django logs
docker logs -f auto-bot-django_app-1

# Nginx logs
docker logs -f auto-bot-nginx-1

# Database logs
docker logs -f auto-bot-db-1
```

### فحص الحالة
```bash
# فحص صحة الخدمات
curl http://localhost:8888/health/

# فحص webhook البوت
curl -X POST http://localhost:8000/bot/webhook/telegram/ \
     -H "Content-Type: application/json" \
     -d '{"test": true}'
```

## 🤝 المساهمة

1. Fork المشروع
2. إنشاء branch جديد (`git checkout -b feature/amazing-feature`)
3. Commit التغييرات (`git commit -m 'Add amazing feature'`)
4. Push للـ branch (`git push origin feature/amazing-feature`)
5. إنشاء Pull Request

## 📄 الترخيص

هذا المشروع مرخص تحت ترخيص MIT - راجع ملف [LICENSE](LICENSE) للتفاصيل.

## 📞 التواصل

- **Email**: contact@tashaleeh.com
- **Website**: https://tashaleeh.com
- **Dashboard**: https://dashboard.tashaleeh.com

---

© 2024 تشاليح. جميع الحقوق محفوظة.