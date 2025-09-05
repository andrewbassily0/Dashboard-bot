# n8n Workflows for Auto Parts Bot

هذا المجلد يحتوي على workflows جاهزة لـ n8n لاستخدامها مع بوت قطع غيار السيارات.

## 📋 Workflows المتاحة

### 1. New Request Workflow (`new_request_workflow.json`)
**الوظيفة**: معالجة الطلبات الجديدة من البوت
**المدخلات**: Webhook من البوت
**المخرجات**: 
- إنشاء طلب في قاعدة البيانات
- إشعار المخازن في المدينة
- تأكيد للعميل

**الخطوات**:
1. استقبال webhook من البوت
2. التحقق من نوع المستخدم
3. إنشاء الطلب عبر Django API
4. البحث عن المخازن في المدينة
5. إرسال إشعارات للمخازن
6. تأكيد للعميل

### 2. New Offer Workflow (`new_offer_workflow.json`)
**الوظيفة**: معالجة العروض الجديدة من المخازن
**المدخلات**: Webhook من البوت
**المخرجات**:
- إنشاء عرض في قاعدة البيانات
- إشعار العميل بالعرض الجديد

**الخطوات**:
1. استقبال webhook من البوت
2. إنشاء العرض عبر Django API
3. الحصول على تفاصيل الطلب
4. إرسال إشعار للعميل

### 3. Scheduled Notifications Workflow (`scheduled_notifications.json`)
**الوظيفة**: إشعارات مجدولة للطلبات التي تنتهي قريباً
**المدخلات**: Cron trigger (كل 6 ساعات)
**المخرجات**:
- تنبيه العملاء بالطلبات المنتهية
- إمكانية تمديد الطلبات

**الخطوات**:
1. تشغيل كل 6 ساعات
2. البحث عن الطلبات التي تنتهي خلال ساعتين
3. إرسال تنبيهات للعملاء
4. معالجة طلبات التمديد

## 🚀 كيفية الاستيراد

### الطريقة الأولى: استيراد يدوي
1. افتح n8n: `http://localhost:5678`
2. اذهب إلى "Workflows" → "Import from file"
3. اختر ملف JSON المطلوب
4. اضغط "Import"

### الطريقة الثانية: استيراد عبر API
```bash
# استيراد workflow الطلبات الجديدة
curl -X POST "http://localhost:5678/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic YWRtaW46YWRtaW4xMjM=" \
  -d @new_request_workflow.json

# استيراد workflow العروض الجديدة
curl -X POST "http://localhost:5678/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic YWRtaW46YWRtaW4xMjM=" \
  -d @new_offer_workflow.json

# استيراد workflow الإشعارات المجدولة
curl -X POST "http://localhost:5678/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic YWRtaW46YWRtaW4xMjM=" \
  -d @scheduled_notifications.json
```

## ⚙️ إعداد المتغيرات البيئية

### في n8n
1. اذهب إلى "Settings" → "Variables"
2. أضف المتغيرات التالية:

| المتغير | القيمة | الوصف |
|---------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | `7761835962:AAFoVhqWW3tU9podafzXVIxhF8t8BYoceYY` | Token البوت |
| `DJANGO_API_URL` | `http://django_app:8000` | رابط Django API |
| `N8N_WEBHOOK_URL` | `http://localhost:5678` | رابط n8n webhook |

### في Docker Compose
```yaml
environment:
  - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  - DJANGO_API_URL=http://django_app:8000
  - N8N_WEBHOOK_URL=http://localhost:5678
```

## 🔧 اختبار Workflows

### 1. اختبار New Request Workflow
```bash
curl -X POST "http://localhost:5678/webhook/new-request" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "user_telegram_id": 123456789,
    "city_id": 1,
    "brand_id": 1,
    "model_id": 1,
    "year": 2020,
    "parts": "مكابح أمامية",
    "media_files": [],
    "request_type": "client"
  }'
```

### 2. اختبار New Offer Workflow
```bash
curl -X POST "http://localhost:5678/webhook/new-offer" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 1,
    "junkyard_id": 1,
    "price": 500,
    "description": "قطع أصلية",
    "delivery_time": "3 أيام"
  }'
```

## 📊 مراقبة Workflows

### 1. مراقبة التنفيذ
- اذهب إلى "Executions" في n8n
- راقب نجاح/فشل كل workflow
- تحقق من السجلات للأخطاء

### 2. مراقبة Webhooks
- اذهب إلى "Webhooks" في n8n
- تحقق من حالة كل webhook
- انسخ URLs للاستخدام في Django

### 3. مراقبة Cron Jobs
- تحقق من تشغيل Cron Trigger
- راقب الإشعارات المجدولة
- تحقق من توقيت التنفيذ

## 🛠️ استكشاف الأخطاء

### مشاكل شائعة:

1. **Webhook لا يستجيب**:
   - تحقق من تشغيل n8n
   - تحقق من صحة URL
   - تحقق من إعدادات CORS

2. **خطأ في الاتصال بـ Django**:
   - تحقق من تشغيل Django
   - تحقق من صحة API endpoints
   - تحقق من إعدادات الشبكة

3. **خطأ في Telegram API**:
   - تحقق من صحة Bot Token
   - تحقق من صلاحيات البوت
   - تحقق من قيود API

### أوامر مفيدة:
```bash
# مراقبة سجلات n8n
docker-compose logs n8n

# مراقبة سجلات Django
docker-compose logs django_app

# اختبار اتصال n8n
curl http://localhost:5678/healthz

# اختبار اتصال Django
curl http://localhost:8000/health/
```

## 🔄 تحديث Workflows

### عند تحديث الكود:
1. تصدير Workflows الحالية
2. تحديث ملفات JSON
3. استيراد النسخ المحدثة
4. اختبار الوظائف الجديدة

### نسخ احتياطي:
```bash
# تصدير جميع Workflows
curl -X GET "http://localhost:5678/api/v1/workflows" \
  -H "Authorization: Basic YWRtaW46YWRtaW4xMjM=" \
  > workflows_backup.json
```

## 📞 الدعم الفني

للحصول على المساعدة:
1. راجع سجلات n8n
2. راجع سجلات Django
3. تحقق من حالة الخدمات
4. راجع إعدادات المتغيرات البيئية

---

**ملاحظة**: تأكد من تشغيل جميع الخدمات قبل اختبار Workflows 