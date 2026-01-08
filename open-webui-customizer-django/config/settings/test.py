"""
Test settings for Django project.
"""

from .development import *

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Password hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Email backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Media files
MEDIA_ROOT = '/tmp/test_media'
STATIC_ROOT = '/tmp/test_static'

# Celery configuration for testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Security for testing
SECRET_KEY = 'test-secret-key-for-testing-only'

# Debug toolbar (disable in tests)
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: False,
}

# Logging for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
}

# Cache configuration for testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Test-specific settings
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Disable debug for faster tests
DEBUG = False

# Template debug
TEMPLATES[0]['OPTIONS']['debug'] = False

# File storage
DEFAULT_FILE_STORAGE = 'django.core.files.storage.InMemoryStorage'

# Reduce operations for faster tests
PIPELINE_MAX_CONCURRENT_BUILDS = 1  # Reduce for testing
GIT_TIMEOUT = 10  # Reduce timeout for testing
REGISTRY_TIMEOUT = 10  # Reduce timeout for testing