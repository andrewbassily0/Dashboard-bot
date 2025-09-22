# 🤝 دليل المساهمة | Contributing Guide

نرحب بمساهماتكم في مشروع **تشاليح - قطع غيار السيارات**! هذا الدليل سيساعدك على المساهمة بشكل فعال.

We welcome contributions to the **Tashaleeh Auto Parts Bot** project! This guide will help you contribute effectively.

## 📋 كيفية المساهمة | How to Contribute

### 1. إعداد بيئة التطوير | Setting up Development Environment

```bash
# استنساخ المشروع
git clone https://github.com/andrewbassily0/Dashboard-bot.git
cd Dashboard-bot

# إعداد Docker
docker-compose up -d db redis

# إعداد Python environment
cd django_app
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# إعداد قاعدة البيانات
python manage.py migrate
python manage.py createsuperuser
```

### 2. أنواع المساهمات | Types of Contributions

#### 🐛 إصلاح الأخطاء | Bug Fixes
- ابحث عن الأخطاء في Issues
- أنشئ branch جديد للإصلاح
- اختبر الإصلاح جيداً
- أرسل Pull Request

#### ✨ ميزات جديدة | New Features
- ناقش الميزة في Issues أولاً
- أنشئ branch للميزة
- اتبع معايير الكود
- أضف اختبارات للميزة

#### 📚 تحسين الوثائق | Documentation Improvements
- تحسين README
- إضافة تعليقات للكود
- كتابة دليل المستخدم
- ترجمة الوثائق

#### 🎨 تحسينات التصميم | UI/UX Improvements
- تحسين واجهة البوت
- تحسين لوحة التحكم
- إضافة رسوم متحركة
- تحسين الاستجابة

### 3. معايير الكود | Code Standards

#### Python/Django
```python
# استخدم Black للـ formatting
black .

# استخدم isort لترتيب الـ imports
isort .

# استخدم flake8 للـ linting
flake8 .
```

#### HTML/CSS/JavaScript
```bash
# استخدم Prettier للـ formatting
prettier --write "**/*.{html,css,js}"

# استخدم ESLint للـ JavaScript
eslint static/dashboard/js/
```

#### Git Commit Messages
```
feat: إضافة ميزة جديدة
fix: إصلاح خطأ
docs: تحديث الوثائق
style: تحسين التنسيق
refactor: إعادة هيكلة الكود
test: إضافة اختبارات
chore: مهام الصيانة
```

### 4. عملية المساهمة | Contribution Process

#### الخطوة 1: Fork المشروع
1. اذهب إلى [المشروع على GitHub](https://github.com/andrewbassily0/Dashboard-bot)
2. اضغط على "Fork" في الزاوية العلوية اليمنى

#### الخطوة 2: إنشاء Branch
```bash
git checkout -b feature/your-feature-name
# أو
git checkout -b fix/your-bug-fix
```

#### الخطوة 3: إجراء التغييرات
- اكتب كود نظيف ومفهوم
- أضف تعليقات باللغة العربية
- اتبع معايير المشروع
- اختبر التغييرات

#### الخطوة 4: الاختبار
```bash
# تشغيل الاختبارات
python manage.py test

# فحص جودة الكود
flake8 .
black --check .
```

#### الخطوة 5: Commit التغييرات
```bash
git add .
git commit -m "feat: إضافة ميزة جديدة للبوت"
```

#### الخطوة 6: Push و Pull Request
```bash
git push origin feature/your-feature-name
```
ثم أنشئ Pull Request على GitHub

### 5. إرشادات خاصة | Specific Guidelines

#### للبوت | For Bot Development
- استخدم اللغة العربية في الرسائل
- اتبع نمط المحادثة الموجود
- أضف معالجة للأخطاء
- اختبر مع مستخدمين حقيقيين

#### للوحة التحكم | For Dashboard Development
- استخدم التصميم الداكن الموجود
- اجعل الواجهة متجاوبة
- أضف رسائل تأكيد للعمليات
- اختبر على أحجام شاشات مختلفة

#### لقاعدة البيانات | For Database Changes
- أنشئ migrations صحيحة
- لا تحذف البيانات الموجودة
- أضف indexes للاستعلامات البطيئة
- اختبر على بيانات كبيرة

### 6. اختبار المساهمة | Testing Your Contribution

#### اختبار البوت | Bot Testing
```bash
# تشغيل البوت في وضع التطوير
python manage.py run_telegram_bot

# اختبار تدفق العملاء
python manage.py test bot.tests_customer_flow

# اختبار نظام التسعير
python manage.py test bot.tests_pricing
```

#### اختبار لوحة التحكم | Dashboard Testing
```bash
# تشغيل الخادم
python manage.py runserver

# فتح المتصفح
# http://localhost:8000/admin/
# http://localhost:8000/dashboard/
```

#### اختبار API | API Testing
```bash
# اختبار endpoints
python manage.py test bot.tests

# اختبار مع curl
curl -X GET http://localhost:8000/api/requests/
```

### 7. حل المشاكل الشائعة | Common Issues

#### مشاكل Docker
```bash
# إعادة بناء الصور
docker-compose build --no-cache

# تنظيف الحاويات
docker-compose down -v
docker system prune -a
```

#### مشاكل قاعدة البيانات
```bash
# إعادة تعيين قاعدة البيانات
docker-compose down -v
docker-compose up -d db
python manage.py migrate
```

#### مشاكل البوت
```bash
# فحص الـ token
echo $TELEGRAM_BOT_TOKEN

# فحص السجلات
tail -f logs/django.log
```

### 8. الحصول على المساعدة | Getting Help

- **GitHub Issues**: للمشاكل والأسئلة
- **Discussions**: للمناقشات العامة
- **Email**: [your-email@example.com]
- **Telegram**: [@your_username]

### 9. الاعتراف بالمساهمين | Recognition

جميع المساهمين سيتم ذكرهم في:
- ملف README.md
- صفحة المساهمين على GitHub
- ملاحظات الإصدار

## 📝 قائمة المراجعة | Checklist

قبل إرسال Pull Request، تأكد من:

- [ ] الكود يتبع معايير المشروع
- [ ] تم اختبار التغييرات
- [ ] تم تحديث الوثائق
- [ ] رسائل Commit واضحة
- [ ] لا توجد أخطاء في الاختبارات
- [ ] الكود قابل للقراءة والفهم

## 🎉 شكراً لمساهمتكم!

مساهماتكم تجعل المشروع أفضل للجميع. شكراً لوقتكم وجهدكم!

---

<div align="center">
  <strong>معاً نبني مستقبل أفضل لقطاع قطع غيار السيارات</strong><br>
  <em>Together we build a better future for the auto parts industry</em>
</div>
