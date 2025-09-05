# بوت قطع غيار السيارات - دليل الاستخدام العربي

## 🚨 حل المشاكل الشائعة

### المشكلة 1: "Cannot close a running event loop"
**السبب**: مشكلة في إدارة asyncio
**الحل**: تم إصلاح الملفات، استخدم `fix_bot.py` بدلاً من `manage_bot.py`

### المشكلة 2: "TELEGRAM_WEBHOOK_URL not found"
**السبب**: متغير بيئي مفقود
**الحل**: تم إنشاء ملف `.env` مع القيم المطلوبة

### المشكلة 3: "coroutine was never awaited"
**السبب**: عدم انتظار coroutines
**الحل**: تم إصلاح `telegram_bot.py`

## 🚀 التشغيل السريع

### 1. إعداد المتغيرات البيئية
```bash
# تعديل ملف .env
nano .env

# تأكد من إضافة:
TELEGRAM_BOT_TOKEN=your_real_bot_token_here
```

### 2. تشغيل المشروع
```bash
# استخدام السكريبت التلقائي
./setup_bot.sh

# أو يدوياً:
docker-compose up -d
```

### 3. تشغيل البوت
```bash
# للتطوير (الأفضل للاختبار)
docker-compose exec django_app python fix_bot.py

# أو استخدام manage_bot.py (بعد الإصلاح)
docker-compose exec django_app python manage_bot.py polling
```

## 🔧 الملفات المحدثة

### `manage_bot.py` ✅
- إصلاح مشاكل asyncio
- إضافة معالجة أفضل للأخطاء
- إدارة صحيحة لـ event loop

### `telegram_bot.py` ✅
- إصلاح إدارة Application
- معالجة أفضل للأخطاء
- تسجيل أفضل للعمليات

### `settings.py` ✅
- قيم افتراضية أفضل
- معالجة المتغيرات البيئية
- إعدادات محسنة

### `fix_bot.py` 🆕
- سكريبت جديد لإصلاح المشاكل
- إدارة أفضل للبوت
- معالجة صحيحة للإشارات

## 📱 كيفية الحصول على Bot Token

### 1. إنشاء بوت جديد
- اذهب إلى @BotFather في تليجرام
- اكتب `/newbot`
- اتبع التعليمات
- احصل على Token

### 2. إضافة Token للمشروع
```bash
# تعديل ملف .env
nano .env

# تغيير السطر:
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

## 🧪 اختبار البوت

### 1. تشغيل البوت
```bash
docker-compose exec django_app python fix_bot.py
```

### 2. اختبار في تليجرام
- ابحث عن بوتك
- اكتب `/start`
- تأكد من استجابة البوت

### 3. مراقبة السجلات
```bash
# مراقبة سجلات Django
docker-compose logs -f django_app

# مراقبة سجلات البوت
docker-compose exec django_app tail -f logs/django.log
```

## 🛠️ أوامر مفيدة

### إدارة المشروع
```bash
# إيقاف المشروع
docker-compose down

# إعادة تشغيل
docker-compose restart

# إعادة بناء
docker-compose build --no-cache
```

### إدارة قاعدة البيانات
```bash
# تشغيل migrations
docker-compose exec django_app python manage.py migrate

# إنشاء superuser
docker-compose exec django_app python manage.py createsuperuser

# ملء البيانات
docker-compose exec django_app python manage.py populate_data
```

### إدارة البوت
```bash
# تشغيل polling
docker-compose exec django_app python fix_bot.py

# إيقاف البوت
# اضغط Ctrl+C في terminal البوت
```

## 🔍 استكشاف الأخطاء

### البوت لا يستجيب
1. تأكد من صحة Token
2. تحقق من تشغيل البوت
3. راجع السجلات

### مشاكل قاعدة البيانات
1. تأكد من تشغيل PostgreSQL
2. تحقق من migrations
3. راجع سجلات db

### مشاكل Docker
1. تأكد من تشغيل Docker
2. تحقق من الحاويات: `docker-compose ps`
3. راجع السجلات: `docker-compose logs`

## 📊 الوصول للخدمات

| الخدمة | الرابط | المستخدم | كلمة المرور |
|--------|--------|----------|-------------|
| الداشبورد | http://localhost | - | - |
| Django Admin | http://localhost/admin/ | admin | admin123 |
| n8n | http://localhost:5678 | admin | admin123 |

## 🎯 الخطوات التالية

### 1. اختبار البوت
- تأكد من استجابة البوت
- اختبر إنشاء طلب
- اختبر إرسال عرض

### 2. تخصيص النظام
- تعديل الرسائل
- إضافة مدن جديدة
- إضافة ماركات جديدة

### 3. إعداد الإنتاج
- تغيير DEBUG إلى False
- إعداد webhook
- تأمين النظام

## 📞 الدعم الفني

إذا واجهت مشاكل:
1. راجع هذا الدليل
2. تحقق من السجلات
3. تأكد من إعدادات Docker
4. تحقق من المتغيرات البيئية

## 🎉 تم الإصلاح!

جميع المشاكل الشائعة تم حلها:
- ✅ مشاكل asyncio
- ✅ متغيرات بيئية مفقودة
- ✅ إدارة Application
- ✅ معالجة الأخطاء

البوت جاهز للاستخدام! 🚀 