# 🚀 دليل n8n السريع - Auto Parts Bot

## ⚡ البدء السريع

### 1. الوصول إلى n8n
```
URL: http://localhost:5678
Username: admin
Password: admin123
```

### 2. استيراد Workflows
```bash
# تشغيل script الاستيراد التلقائي
./n8n/import_workflows.sh

# أو استيراد يدوي
# 1. اذهب إلى Workflows → Import from file
# 2. اختر ملف JSON من مجلد workflows
# 3. اضغط Import
```

### 3. تفعيل Workflows
- اذهب إلى "Workflows"
- اضغط على "Activate" لكل workflow
- تأكد من أن الحالة "Active"

## 📋 Workflows المتاحة

### 🔄 New Request Workflow
**الوظيفة**: معالجة الطلبات الجديدة
**Webhook URL**: `http://localhost:5678/webhook/new-request`
**المدخلات**: بيانات الطلب من البوت
**المخرجات**: إنشاء طلب + إشعار المخازن

### 💰 New Offer Workflow
**الوظيفة**: معالجة العروض الجديدة
**Webhook URL**: `http://localhost:5678/webhook/new-offer`
**المدخلات**: بيانات العرض من المخزن
**المخرجات**: إنشاء عرض + إشعار العميل

### ⏰ Scheduled Notifications
**الوظيفة**: إشعارات مجدولة
**التوقيت**: كل 6 ساعات
**المخرجات**: تنبيهات انتهاء الصلاحية

## 🔧 اختبار Workflows

### اختبار New Request
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
    "request_type": "client"
  }'
```

### اختبار New Offer
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

## 📊 مراقبة النظام

### 1. مراقبة Workflows
- **Workflows**: `http://localhost:5678/workflows`
- **Executions**: `http://localhost:5678/executions`
- **Webhooks**: `http://localhost:5678/webhooks`

### 2. مراقبة السجلات
```bash
# سجلات n8n
docker-compose logs n8n

# سجلات Django
docker-compose logs django_app

# سجلات Redis
docker-compose logs redis
```

### 3. فحص الصحة
```bash
# فحص n8n
curl http://localhost:5678/healthz

# فحص Django
curl http://localhost:8000/health/

# فحص Redis
docker-compose exec redis redis-cli ping
```

## ⚙️ إعداد المتغيرات البيئية

### في n8n Dashboard
1. اذهب إلى "Settings" → "Variables"
2. أضف المتغيرات التالية:

| المتغير | القيمة | الوصف |
|---------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | `7761835962:AAFoVhqWW3tU9podafzXVIxhF8t8BYoceYY` | Token البوت |
| `DJANGO_API_URL` | `http://django_app:8000` | رابط Django API |

### في Docker Compose
```bash
# تعيين المتغيرات
export TELEGRAM_BOT_TOKEN="7761835962:AAFoVhqWW3tU9podafzXVIxhF8t8BYoceYY"

# إعادة تشغيل
docker-compose down
docker-compose up -d
```

## 🛠️ استكشاف الأخطاء

### مشاكل شائعة:

1. **Webhook لا يستجيب**
   - تحقق من تشغيل n8n
   - تحقق من صحة URL
   - تحقق من إعدادات CORS

2. **خطأ في الاتصال بـ Django**
   - تحقق من تشغيل Django
   - تحقق من صحة API endpoints
   - تحقق من إعدادات الشبكة

3. **خطأ في Telegram API**
   - تحقق من صحة Bot Token
   - تحقق من صلاحيات البوت

### أوامر مفيدة:
```bash
# إعادة تشغيل n8n
docker-compose restart n8n

# إعادة بناء n8n
docker-compose build n8n

# مسح بيانات n8n
docker-compose down -v
docker-compose up -d
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

## 📱 ربط البوت مع n8n

### في Django Bot:
```python
# إرسال webhook إلى n8n
import requests

def send_to_n8n(webhook_type, data):
    n8n_url = f"http://n8n:5678/webhook/{webhook_type}"
    response = requests.post(n8n_url, json=data)
    return response.json()

# مثال: إرسال طلب جديد
send_to_n8n("new-request", {
    "user_id": user.id,
    "user_telegram_id": user.telegram_id,
    "city_id": city.id,
    "brand_id": brand.id,
    "model_id": model.id,
    "year": year,
    "parts": parts,
    "request_type": "client"
})
```

## 🎯 الخطوات التالية

1. **اختبار Workflows**: تأكد من عمل جميع workflows
2. **ربط البوت**: أضف webhook calls في Django Bot
3. **إعداد قاعدة البيانات**: تشغيل migrations وإضافة بيانات أساسية
4. **اختبار النظام**: اختبر البوت مع workflows

## 📞 الدعم الفني

للحصول على المساعدة:
1. راجع سجلات n8n
2. راجع سجلات Django
3. تحقق من حالة الخدمات
4. راجع إعدادات المتغيرات البيئية

---

**ملاحظة**: تأكد من تشغيل جميع الخدمات قبل اختبار Workflows 