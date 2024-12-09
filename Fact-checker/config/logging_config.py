"""
تنظیمات لاگ‌گیری برنامه.
این ماژول شامل پیکربندی‌های مربوط به نحوه ثبت رویدادها و خطاهاست.
"""

import os
from pathlib import Path
from config.config import LOGS_DIR

# تنظیمات پایه لاگینگ
BASE_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: '
                     '%(message)s - %(funcName)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'json': {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue'
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'app.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 مگابایت
            'backupCount': 5,
            'formatter': 'detailed',
            'encoding': 'utf-8'
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'error.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'detailed',
            'encoding': 'utf-8'
        },
        'json_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'json.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'json',
            'encoding': 'utf-8'
        }
    },
    'loggers': {
        '': {  # ریشه - پیش‌فرض برای تمام ماژول‌ها
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True
        },
        'factchecker': {  # لاگر اختصاصی برنامه
            'handlers': ['console', 'file', 'json_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'factchecker.core': {  # لاگر هسته اصلی
            'handlers': ['file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'factchecker.bot': {  # لاگر بات تلگرام
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False
        },
        'factchecker.data': {  # لاگر دسترسی به داده
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}

# تنظیمات اضافی برای محیط توسعه
DEVELOPMENT_LOGGING = {
    'handlers': {
        'debug_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'debug.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 3,
            'formatter': 'detailed',
            'encoding': 'utf-8'
        }
    },
    'loggers': {
        'factchecker': {
            'handlers': ['console', 'file', 'debug_file'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}

# تنظیمات اضافی برای محیط تولید
PRODUCTION_LOGGING = {
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.handlers.logging.SentryHandler',
            'dsn': os.getenv('SENTRY_DSN'),
        }
    },
    'loggers': {
        'factchecker': {
            'handlers': ['mail_admins', 'sentry', 'json_file'],
            'level': 'WARNING',
            'propagate': False
        }
    }
}

# انتخاب تنظیمات بر اساس محیط اجرا
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

if ENVIRONMENT == 'development':
    LOGGING_CONFIG = {
        **BASE_LOGGING,
        **DEVELOPMENT_LOGGING
    }
elif ENVIRONMENT == 'production':
    LOGGING_CONFIG = {
        **BASE_LOGGING,
        **PRODUCTION_LOGGING
    }
else:
    LOGGING_CONFIG = BASE_LOGGING

# تنظیمات جمع‌آوری متریک‌ها
METRICS_CONFIG = {
    'enable_metrics': True,
    'metrics_handlers': ['statsd', 'prometheus'],
    'metrics_prefix': 'factchecker',
    'collect_intervals': {
        'basic': 60,  # هر دقیقه
        'detailed': 300,  # هر 5 دقیقه
        'performance': 30  # هر 30 ثانیه
    }
}