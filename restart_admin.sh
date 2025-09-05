#!/bin/bash

# Script to restart Django application after admin save fix
# إعادة تشغيل Django بعد إصلاح مشكلة الحفظ في الإدارة

echo "🔄 إعادة تشغيل Django لتطبيق إصلاح أزرار الحفظ..."
echo "Restarting Django to apply admin save fix..."

# Stop and start Django service
docker-compose restart django_app

echo "✅ تم إعادة التشغيل بنجاح!"
echo "✅ Django restarted successfully!"

echo ""
echo "🧪 يمكنك الآن اختبار إضافة مستخدم أو junkyard جديد:"
echo "🧪 You can now test adding a new user or junkyard:"
echo "   - انتقل إلى /admin/"
echo "   - Go to /admin/"
echo "   - جرب إضافة مستخدم جديد أو junkyard"
echo "   - Try adding a new user or junkyard"
echo "   - اضغط 'حفظ' وتأكد من حفظ البيانات"
echo "   - Click 'Save' and verify data is saved"

echo ""
echo "📋 إذا استمرت المشكلة، راجع ملف ADMIN_SAVE_ISSUE_SOLUTION.md"
echo "📋 If the issue persists, check ADMIN_SAVE_ISSUE_SOLUTION.md"
