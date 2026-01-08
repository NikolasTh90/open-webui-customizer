"""
Development settings - mirrors FastAPI's DevSettings.
"""

from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Development database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'dev.sqlite3',
    }
}

# CORS - Allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Relaxed security for development
SECRET_KEY = 'dev-secret-key-not-for-production'
ENCRYPTION_KEY = 'dev-encryption-key-32-bytes-long'

# Git settings - relaxed for development
GIT_TIMEOUT = 3600
GIT_ALLOW_ANY_HOST = True

# Pipeline settings - relaxed for development
PIPELINE_BUILD_TIMEOUT = 3600
PIPELINE_MAX_CONCURRENT_BUILDS = 1

# Debug logging
LOGGING['root']['level'] = 'DEBUG'
LOGGING['handlers']['console']['formatter'] = 'verbose'

# Debug toolbar (install django-debug-toolbar to enable)
if 'debug_toolbar' in INSTALLED_APPS:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']