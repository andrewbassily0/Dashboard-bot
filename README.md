# 🚗 تشاليح - قطع غيار السيارات | Auto Parts Bot

[![Django](https://img.shields.io/badge/Django-4.2.7-green.svg)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4.svg)](https://core.telegram.org/bots)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 نظرة عامة | Overview

**تشاليح** هو نظام متكامل لإدارة قطع غيار السيارات المستعملة، يتضمن بوت تليجرام ذكي ولوحة تحكم إدارية متقدمة. النظام يربط بين العملاء الذين يبحثون عن قطع غيار محددة وبين تشاليح السيارات التي تمتلك هذه القطع.

**Tashaleeh** is a comprehensive auto parts management system featuring an intelligent Telegram bot and advanced admin dashboard. The system connects customers seeking specific auto parts with junkyards that have those parts in stock.

## ✨ المميزات الرئيسية | Key Features

### 🤖 بوت تليجرام ذكي | Smart Telegram Bot
- **واجهة تفاعلية باللغة العربية** - Interactive Arabic interface
- **نظام طلبات متقدم** - Advanced request system
- **إدارة العروض والتفاوض** - Offer management and negotiation
- **نظام تقييم التشاليح** - Junkyard rating system
- **إشعارات ذكية** - Smart notifications
- **دعم الوسائط المتعددة** - Multimedia support

### 🎛️ لوحة تحكم إدارية | Admin Dashboard
- **تصميم احترافي داكن** - Professional dark theme
- **إدارة المستخدمين والتشاليح** - User and junkyard management
- **تحليلات متقدمة** - Advanced analytics
- **نظام إشعارات متكامل** - Integrated notification system
- **واجهة متجاوبة** - Responsive interface

### 🔧 نظام إدارة متقدم | Advanced Management System
- **إدارة الطلبات والعروض** - Request and offer management
- **نظام العمولات** - Commission system
- **تتبع الحالة** - Status tracking
- **تقارير مفصلة** - Detailed reports

## 🏗️ البنية التقنية | Technical Architecture

### التقنيات المستخدمة | Technologies Used
- **Backend**: Django 4.2.7 + Django REST Framework
- **Database**: PostgreSQL 15
- **Bot**: Python Telegram Bot 20.7
- **Frontend**: HTML5, CSS3, JavaScript, Tailwind CSS
- **Automation**: N8N Workflow Automation
- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx
- **Cache**: Redis

### هيكل المشروع | Project Structure
```
Dashboard-bot/
├── django_app/                 # Django application
│   ├── auto_parts_bot/         # Main Django project
│   ├── bot/                    # Telegram bot app
│   ├── dashboard/              # Admin dashboard app
│   ├── static/                 # Static files
│   ├── templates/              # HTML templates
│   └── requirements.txt        # Python dependencies
├── n8n/                       # N8N workflows
├── nginx/                     # Nginx configuration
├── docker-compose.yml         # Docker services
└── README.md                  # This file
```

## 🚀 التثبيت والتشغيل | Installation & Setup

### المتطلبات | Prerequisites
- Docker & Docker Compose
- Git
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### خطوات التثبيت | Installation Steps

1. **استنساخ المشروع | Clone the repository**
```bash
git clone https://github.com/andrewbassily0/Dashboard-bot.git
cd Dashboard-bot
```

2. **إعداد متغيرات البيئة | Environment Variables**
```bash
# إنشاء ملف .env
cp .env.example .env

# تعديل المتغيرات المطلوبة
TELEGRAM_BOT_TOKEN=your_bot_token_here
DJANGO_SECRET_KEY=your_secret_key_here
DEBUG=False
```

3. **تشغيل الخدمات | Start Services**
```bash
# تشغيل جميع الخدمات
docker-compose up -d

# أو تشغيل خدمة معينة
docker-compose up -d db redis django_app
```

4. **إعداد قاعدة البيانات | Database Setup**
```bash
# إنشاء migrations
docker-compose exec django_app python manage.py makemigrations

# تطبيق migrations
docker-compose exec django_app python manage.py migrate

# إنشاء superuser
docker-compose exec django_app python manage.py createsuperuser
```

5. **تشغيل البوت | Start the Bot**
```bash
# تشغيل البوت
docker-compose exec django_app python manage.py run_telegram_bot

# أو تشغيل البوت في الخلفية
docker-compose exec -d django_app python manage.py run_telegram_bot
```

## 🌐 الوصول للخدمات | Service Access

| Service | URL | Description |
|---------|-----|-------------|
| **Admin Dashboard** | http://localhost:8000/admin/ | لوحة التحكم الإدارية |
| **API Endpoints** | http://localhost:8000/api/ | REST API endpoints |
| **N8N Workflows** | http://localhost:5678/ | N8N automation platform |
| **Nginx Proxy** | http://localhost:8888/ | Web server proxy |

### بيانات الدخول الافتراضية | Default Credentials
- **N8N**: admin / admin123
- **Django Admin**: (يتم إنشاؤها عند setup)

## 📱 استخدام البوت | Bot Usage

### للأعمالاء | For Customers
1. ابدأ محادثة مع البوت: `/start`
2. اختر "طلب قطع غيار"
3. املأ تفاصيل الطلب (نوع السيارة، القطعة المطلوبة، إلخ)
4. انتظر العروض من التشاليح
5. قارن العروض واختر الأفضل

### للتشاليح | For Junkyards
1. سجل حساب كـ "تشليح"
2. أضف معلومات التشليح (الموقع، الهاتف، إلخ)
3. استقبل إشعارات الطلبات الجديدة
4. أرسل عروضك للعملاء
5. تفاوض على الأسعار

## 🔧 التطوير | Development

### إعداد بيئة التطوير | Development Setup
```bash
# تثبيت dependencies
pip install -r django_app/requirements.txt

# تشغيل Django development server
cd django_app
python manage.py runserver

# تشغيل البوت في وضع التطوير
python manage.py run_telegram_bot
```

### إدارة البيانات | Data Management
```bash
# إنشاء بيانات تجريبية
python manage.py populate_data

# إصلاح أنواع المستخدمين
python manage.py fix_user_types

# إصلاح سريع للتشاليح
python manage.py quick_fix
```

### الاختبار | Testing
```bash
# تشغيل جميع الاختبارات
python manage.py test

# اختبار تدفق العملاء
python manage.py test bot.tests_customer_flow

# اختبار نظام التسعير
python manage.py test bot.tests_pricing
```

## 📊 الميزات المتقدمة | Advanced Features

### 🤖 نظام N8N للعمل التلقائي
- **إشعارات تلقائية** - Automatic notifications
- **معالجة الطلبات** - Request processing
- **إدارة العروض** - Offer management
- **تقارير دورية** - Periodic reports

### 📈 نظام التحليلات
- **إحصائيات الطلبات** - Request statistics
- **تقييم الأداء** - Performance metrics
- **تقارير المبيعات** - Sales reports
- **تحليل المستخدمين** - User analytics

### 🔐 الأمان والحماية
- **مصادقة متعددة المستويات** - Multi-level authentication
- **تشفير البيانات** - Data encryption
- **حماية من الهجمات** - Attack protection
- **نسخ احتياطية تلقائية** - Automatic backups

## 🛠️ الصيانة والاستكشاف | Maintenance & Troubleshooting

### سجلات النظام | System Logs
```bash
# عرض سجلات Django
docker-compose logs django_app

# عرض سجلات البوت
docker-compose logs django_app | grep "telegram"

# عرض سجلات قاعدة البيانات
docker-compose logs db
```

### إعادة تشغيل الخدمات | Restart Services
```bash
# إعادة تشغيل جميع الخدمات
docker-compose restart

# إعادة تشغيل خدمة معينة
docker-compose restart django_app

# إعادة بناء وإعادة تشغيل
docker-compose up --build -d
```

### استكشاف الأخطاء | Troubleshooting
```bash
# فحص حالة الخدمات
docker-compose ps

# فحص استخدام الموارد
docker stats

# فحص الاتصال بقاعدة البيانات
docker-compose exec django_app python manage.py dbshell
```

## 📝 API Documentation

### Endpoints الرئيسية | Main Endpoints

#### المستخدمين | Users
- `GET /api/users/` - قائمة المستخدمين
- `POST /api/users/` - إنشاء مستخدم جديد
- `GET /api/users/{id}/` - تفاصيل مستخدم

#### الطلبات | Requests
- `GET /api/requests/` - قائمة الطلبات
- `POST /api/requests/` - إنشاء طلب جديد
- `PUT /api/requests/{id}/` - تحديث طلب

#### العروض | Offers
- `GET /api/offers/` - قائمة العروض
- `POST /api/offers/` - إنشاء عرض جديد
- `PUT /api/offers/{id}/` - تحديث عرض

## 🤝 المساهمة | Contributing

نرحب بمساهماتكم! يرجى اتباع الخطوات التالية:

1. Fork المشروع
2. إنشاء branch للميزة الجديدة (`git checkout -b feature/AmazingFeature`)
3. Commit التغييرات (`git commit -m 'Add some AmazingFeature'`)
4. Push إلى Branch (`git push origin feature/AmazingFeature`)
5. فتح Pull Request

## 📄 الترخيص | License

هذا المشروع مرخص تحت رخصة MIT - راجع ملف [LICENSE](LICENSE) للتفاصيل.

## 📞 الدعم والاتصال | Support & Contact

- **المطور الرئيسي**: Andrew Bassily
- **البريد الإلكتروني**: [your-email@example.com]
- **GitHub**: [@andrewbassily0](https://github.com/andrewbassily0)
- **الموقع**: [https://dashboard.tashaleeh.com](https://dashboard.tashaleeh.com)

## 🙏 شكر وتقدير | Acknowledgments

- فريق Django للـ framework الرائع
- مجتمع Python Telegram Bot
- جميع المساهمين في المشروع

---

<div align="center">
  <strong>تم تطويره بـ ❤️ في المملكة العربية السعودية</strong><br>
  <em>Developed with ❤️ in Saudi Arabia</em>
</div>
