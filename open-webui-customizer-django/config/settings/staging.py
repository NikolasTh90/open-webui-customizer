"""
Staging settings - mirrors FastAPI's StagingSettings.
"""

from .base import *

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Staging database (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'openwebui_customizer_staging'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
    }
}

# CORS - Specific origins for staging
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', 
    'http://localhost:3000,http://staging.openwebui.example.com'
).split(',')

# Security requirements for staging
SECRET_KEY = os.environ.get('SECRET_KEY')
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')

if not SECRET_KEY or not ENCRYPTION_KEY:
    raise ValueError("SECRET_KEY and ENCRYPTION_KEY must be set in staging")

# Logging - more verbose for staging
LOGGING['root']['level'] = 'INFO'
LOGGING['handlers']['console']['formatter'] = 'verbose'

# Email configuration for staging
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'staging@openwebui.example.com')

# Cache configuration (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Static files serving via WhiteNoise (install whitenoise to enable)
if 'whitenoise' in INSTALLED_APPS:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'