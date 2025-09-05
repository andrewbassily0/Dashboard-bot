module.exports = {
  // إعدادات المصادقة
  basicAuth: {
    active: true,
    user: process.env.N8N_BASIC_AUTH_USER || 'admin',
    password: process.env.N8N_BASIC_AUTH_PASSWORD || 'admin123'
  },

  // إعدادات قاعدة البيانات
  database: {
    type: 'sqlite',
    database: process.env.DB_SQLITE_DATABASE || '/home/node/.n8n/database.sqlite',
    pool: {
      min: 2,
      max: parseInt(process.env.DB_SQLITE_POOL_SIZE) || 10
    }
  },

  // إعدادات Redis
  redis: {
    host: process.env.N8N_QUEUE_BULL_REDIS_HOST || 'redis',
    port: parseInt(process.env.N8N_QUEUE_BULL_REDIS_PORT) || 6379,
    db: parseInt(process.env.N8N_QUEUE_BULL_REDIS_DB) || 0
  },

  // إعدادات Webhook
  webhook: {
    url: process.env.WEBHOOK_URL || 'http://localhost:5678/',
    tunnelUrl: process.env.WEBHOOK_TUNNEL_URL || 'http://localhost:5678/',
    verifySSL: process.env.N8N_WEBHOOK_VERIFY_SSL === 'true'
  },

  // إعدادات التنفيذ
  execution: {
    process: process.env.N8N_EXECUTIONS_PROCESS || 'main',
    mode: process.env.N8N_EXECUTIONS_MODE || 'regular',
    timeout: parseInt(process.env.N8N_EXECUTIONS_TIMEOUT) || 3600,
    timeoutMax: parseInt(process.env.N8N_EXECUTIONS_TIMEOUT_MAX) || 7200
  },

  // إعدادات الطوابير
  queue: {
    bull: {
      redis: {
        host: process.env.N8N_QUEUE_BULL_REDIS_HOST || 'redis',
        port: parseInt(process.env.N8N_QUEUE_BULL_REDIS_PORT) || 6379,
        db: parseInt(process.env.N8N_QUEUE_BULL_REDIS_DB) || 0
      }
    }
  },

  // إعدادات التخزين المؤقت
  cache: {
    backend: process.env.N8N_CACHE_BACKEND || 'redis',
    redis: {
      host: process.env.N8N_CACHE_REDIS_HOST || 'redis',
      port: parseInt(process.env.N8N_CACHE_REDIS_PORT) || 6379,
      db: parseInt(process.env.N8N_CACHE_REDIS_DB) || 1
    }
  },

  // إعدادات السجلات
  logging: {
    level: process.env.N8N_LOG_LEVEL || 'info',
    output: process.env.N8N_LOG_OUTPUT || 'console'
  },

  // إعدادات الأمان
  security: {
    oauth2: {
      disabled: process.env.N8N_SECURITY_OAUTH2_DISABLED === 'true',
      google: {
        disabled: process.env.N8N_SECURITY_OAUTH2_GOOGLE_DISABLED === 'true'
      },
      github: {
        disabled: process.env.N8N_SECURITY_OAUTH2_GITHUB_DISABLED === 'true'
      }
    }
  },

  // إعدادات الحد من المعدل
  rateLimit: {
    windowMs: parseInt(process.env.N8N_RATE_LIMIT_WINDOW) || 60000,
    max: parseInt(process.env.N8N_RATE_LIMIT_MAX) || 1000
  },

  // إعدادات المقاييس
  metrics: {
    enabled: process.env.N8N_METRICS_ENABLED === 'true',
    prefix: process.env.N8N_METRICS_PREFIX || 'n8n'
  },

  // إعدادات فحص الصحة
  healthCheck: {
    enabled: process.env.N8N_HEALTH_CHECK_ENABLED === 'true',
    path: process.env.N8N_HEALTH_CHECK_PATH || '/healthz'
  },

  // إعدادات المحرر
  editor: {
    baseUrl: process.env.N8N_EDITOR_BASE_URL || 'http://localhost:5678/'
  },

  // إعدادات المنطقة الزمنية
  generic: {
    timezone: process.env.GENERIC_TIMEZONE || 'Asia/Riyadh'
  },

  // إعدادات إضافية
  enforceSettingsFilePermissions: process.env.N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS === 'true',
  runnersEnabled: process.env.N8N_RUNNERS_ENABLED === 'true',
  nodeEnv: process.env.NODE_ENV || 'production',

  // إعدادات مخصصة للمشروع
  custom: {
    telegramBotToken: process.env.TELEGRAM_BOT_TOKEN,
    djangoApiUrl: process.env.DJANGO_API_URL || 'http://django_app:8000',
    n8nWebhookUrl: process.env.N8N_WEBHOOK_URL || 'http://localhost:5678'
  }
}; 