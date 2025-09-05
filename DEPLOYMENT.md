# دليل النشر - Auto Parts Ordering Telegram Bot

## نشر المشروع في بيئة الإنتاج

### 1. متطلبات الخادم

#### المواصفات المطلوبة:
- **المعالج**: 2 CPU cores أو أكثر
- **الذاكرة**: 4GB RAM أو أكثر
- **التخزين**: 50GB SSD أو أكثر
- **نظام التشغيل**: Ubuntu 20.04+ أو CentOS 8+
- **الشبكة**: عنوان IP ثابت ونطاق (domain)

#### البرامج المطلوبة:
```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# تثبيت Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# تثبيت Git
sudo apt install git -y

# تثبيت Nginx (للإعداد المتقدم)
sudo apt install nginx -y

# تثبيت Certbot (لشهادات SSL)
sudo apt install certbot python3-certbot-nginx -y
```

### 2. إعداد النطاق والـ DNS

```bash
# إعداد سجلات DNS
# A Record: yourdomain.com -> YOUR_SERVER_IP
# A Record: www.yourdomain.com -> YOUR_SERVER_IP
# A Record: api.yourdomain.com -> YOUR_SERVER_IP (اختياري)
```

### 3. تحميل وإعداد المشروع

```bash
# إنشاء مستخدم للمشروع
sudo useradd -m -s /bin/bash autoparts
sudo usermod -aG docker autoparts
sudo su - autoparts

# تحميل المشروع
git clone <repository-url> auto_parts_bot_project
cd auto_parts_bot_project

# إعداد المتغيرات البيئية للإنتاج
cp .env.example .env
nano .env
```

### 4. تحديث متغيرات الإنتاج

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_real_telegram_bot_token
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/bot/webhook/telegram/

# Database Configuration
DATABASE_URL=postgresql://postgres:STRONG_PASSWORD@db:5432/auto_parts_bot

# Django Configuration
DJANGO_SECRET_KEY=generate-a-very-strong-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com

# n8n Configuration
N8N_WEBHOOK_URL=http://n8n:5678
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=STRONG_N8N_PASSWORD

# Security
SECURE_SSL_REDIRECT=True
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https

# Email Configuration (اختياري)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Logging
LOG_LEVEL=INFO
```

### 5. تحديث docker-compose للإنتاج

إنشاء `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: auto_parts_bot
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    networks:
      - app_network

  django_app:
    build: ./django_app
    command: gunicorn auto_parts_bot.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - ./django_app:/app
      - media_files:/app/media
      - static_files:/app/staticfiles
    depends_on:
      - db
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - DEBUG=False
    restart: unless-stopped
    networks:
      - app_network

  n8n:
    image: n8nio/n8n:latest
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD}
      - WEBHOOK_URL=https://yourdomain.com/
      - GENERIC_TIMEZONE=Asia/Riyadh
      - N8N_SECURE_COOKIE=false
    volumes:
      - n8n_data:/home/node/.n8n
    restart: unless-stopped
    networks:
      - app_network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf
      - static_files:/var/www/static
      - media_files:/var/www/media
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - django_app
    restart: unless-stopped
    networks:
      - app_network

  redis:
    image: redis:alpine
    restart: unless-stopped
    networks:
      - app_network

volumes:
  postgres_data:
  n8n_data:
  media_files:
  static_files:

networks:
  app_network:
    driver: bridge
```

### 6. إعداد Nginx للإنتاج

إنشاء `nginx/nginx.prod.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=webhook:10m rate=100r/s;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    upstream django_app {
        server django_app:8000;
    }

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;
        
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        client_max_body_size 100M;

        # Static files
        location /static/ {
            alias /var/www/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Media files
        location /media/ {
            alias /var/www/media/;
            expires 1M;
            add_header Cache-Control "public";
        }

        # API endpoints with rate limiting
        location /bot/api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://django_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Webhook endpoints with higher rate limit
        location /bot/webhook/ {
            limit_req zone=webhook burst=50 nodelay;
            proxy_pass http://django_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Main application
        location / {
            proxy_pass http://django_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
        }
    }
}
```

### 7. إعداد شهادة SSL

```bash
# الحصول على شهادة SSL مجانية من Let's Encrypt
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# أو نسخ الشهادات يدوياً
sudo mkdir -p ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/
sudo chown -R autoparts:autoparts ssl/
```

### 8. النشر

```bash
# بناء وتشغيل المشروع
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# إعداد قاعدة البيانات
docker-compose -f docker-compose.prod.yml exec django_app python manage.py migrate
docker-compose -f docker-compose.prod.yml exec django_app python manage.py collectstatic --noinput
docker-compose -f docker-compose.prod.yml exec django_app python manage.py populate_data

# إنشاء superuser
docker-compose -f docker-compose.prod.yml exec django_app python manage.py createsuperuser

# إعداد webhook للبوت
docker-compose -f docker-compose.prod.yml exec django_app python manage_bot.py webhook
```

### 9. إعداد النسخ الاحتياطي التلقائي

إنشاء `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/autoparts/auto_parts_bot_project/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# إنشاء مجلد النسخ الاحتياطية
mkdir -p $BACKUP_DIR

# نسخ احتياطي لقاعدة البيانات
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres auto_parts_bot > $BACKUP_DIR/db_backup_$DATE.sql

# نسخ احتياطي للملفات المرفوعة
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz django_app/media/

# حذف النسخ الاحتياطية القديمة (أكثر من 30 يوم)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# جعل الملف قابل للتنفيذ
chmod +x backup.sh

# إضافة مهمة cron للنسخ الاحتياطي اليومي
crontab -e
# إضافة السطر التالي:
# 0 2 * * * /home/autoparts/auto_parts_bot_project/backup.sh >> /home/autoparts/backup.log 2>&1
```

### 10. مراقبة النظام

إنشاء `monitor.sh`:

```bash
#!/bin/bash

# فحص حالة الحاويات
echo "=== Docker Containers Status ==="
docker-compose -f docker-compose.prod.yml ps

# فحص استخدام الموارد
echo "=== Resource Usage ==="
docker stats --no-stream

# فحص السجلات الأخيرة للأخطاء
echo "=== Recent Errors ==="
docker-compose -f docker-compose.prod.yml logs --tail=50 | grep -i error

# فحص مساحة القرص
echo "=== Disk Usage ==="
df -h

# فحص الذاكرة
echo "=== Memory Usage ==="
free -h
```

### 11. إعداد Firewall

```bash
# تفعيل UFW
sudo ufw enable

# السماح بالاتصالات الأساسية
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# منع الوصول المباشر لقاعدة البيانات
sudo ufw deny 5432

# عرض حالة Firewall
sudo ufw status
```

### 12. إعداد Systemd Service (اختياري)

إنشاء `/etc/systemd/system/autoparts-bot.service`:

```ini
[Unit]
Description=Auto Parts Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/autoparts/auto_parts_bot_project
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0
User=autoparts

[Install]
WantedBy=multi-user.target
```

```bash
# تفعيل الخدمة
sudo systemctl enable autoparts-bot.service
sudo systemctl start autoparts-bot.service
```

### 13. اختبار النشر

```bash
# اختبار الموقع
curl -I https://yourdomain.com

# اختبار API
curl https://yourdomain.com/bot/api/stats/

# اختبار webhook
curl -X POST https://yourdomain.com/bot/webhook/telegram/ \
  -H "Content-Type: application/json" \
  -d '{"test": "webhook"}'

# فحص سجلات البوت
docker-compose -f docker-compose.prod.yml logs django_app
```

### 14. إعداد المراقبة المتقدمة (اختياري)

#### تثبيت Prometheus و Grafana:

```yaml
# إضافة إلى docker-compose.prod.yml
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped
```

### 15. التحديث والصيانة

```bash
# تحديث المشروع
git pull origin main

# إعادة بناء الحاويات
docker-compose -f docker-compose.prod.yml build --no-cache

# إعادة تشغيل الخدمات
docker-compose -f docker-compose.prod.yml up -d

# تشغيل migrations جديدة
docker-compose -f docker-compose.prod.yml exec django_app python manage.py migrate

# جمع الملفات الثابتة
docker-compose -f docker-compose.prod.yml exec django_app python manage.py collectstatic --noinput
```

### 16. استكشاف الأخطاء

#### مشاكل شائعة في الإنتاج:

1. **خطأ 502 Bad Gateway:**
   ```bash
   # فحص حالة Django
   docker-compose -f docker-compose.prod.yml logs django_app
   
   # فحص تكوين Nginx
   docker-compose -f docker-compose.prod.yml exec nginx nginx -t
   ```

2. **مشاكل SSL:**
   ```bash
   # تجديد شهادة SSL
   sudo certbot renew
   
   # فحص انتهاء صلاحية الشهادة
   openssl x509 -in ssl/fullchain.pem -text -noout | grep "Not After"
   ```

3. **مشاكل الأداء:**
   ```bash
   # مراقبة استخدام الموارد
   docker stats
   
   # فحص سجلات قاعدة البيانات
   docker-compose -f docker-compose.prod.yml logs db
   ```

### 17. الأمان الإضافي

```bash
# تحديث النظام بانتظام
sudo apt update && sudo apt upgrade -y

# تثبيت fail2ban
sudo apt install fail2ban -y

# تكوين fail2ban للحماية من هجمات القوة الغاشمة
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local

# إعداد تحديث Docker التلقائي
echo '0 4 * * 0 docker system prune -af' | sudo crontab -
```

هذا الدليل يغطي جميع جوانب نشر المشروع في بيئة الإنتاج بشكل آمن وموثوق.

