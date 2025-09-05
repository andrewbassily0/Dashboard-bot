#!/bin/bash

# تحقق من عدم وجود instances أخرى
if pgrep -f "manage_bot.py polling" > /dev/null; then
    echo "❌ البوت يعمل بالفعل! يرجى إيقافه أولاً"
    exit 1
fi

echo "🚀 بدء تشغيل البوت..."

# تشغيل البوت داخل container
docker-compose exec django_app python3 manage_bot.py polling 