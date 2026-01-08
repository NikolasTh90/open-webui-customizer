"""
Base Django settings for Open WebUI Customizer.
Equivalent to FastAPI's app/config/settings.py BaseSettings.
"""

import os
from pathlib import Path
from datetime import timedelta

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
DEBUG = False
ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'unfold',  # Must come before django.contrib.admin

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'corsheaders',
    'drf_spectacular',
    'django_htmx',

    # Local apps
    'apps.core',
    'apps.branding',
    'apps.credentials',
    'apps.pipelines',
    'apps.registries',
    'apps.repositories',
    'apps.dashboard',
]

# Configure Django Unfold
UNFOLD = {
    "SITE_TITLE": "Open WebUI Customizer",
    "SITE_HEADER": "Open WebUI Customizer Admin",
    "SITE_INDEX_TITLE": "Welcome to Open WebUI Customizer Admin Panel",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Dashboard",
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": "/admin/auth/user/",
                    },
                    {
                        "title": "Groups",
                        "icon": "group",
                        "link": "/admin/auth/group/",
                    },
                ],
            },
            {
                "title": "Content Management",
                "items": [
                    {
                        "title": "Branding Templates",
                        "icon": "palette",
                        "link": "/admin/branding/brandingtemplate/",
                    },
                    {
                        "title": "Branding Assets",
                        "icon": "image",
                        "link": "/admin/branding/brandingasset/",
                    },
                    {
                        "title": "Credentials",
                        "icon": "key",
                        "link": "/admin/credentials/credential/",
                    },
                ],
            },
        ],
    },
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django_htmx.middleware.HtmxMiddleware',  # Add after CommonMiddleware
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'config.asgi.application'

# Database configuration (mirrors FastAPI's BaseDatabaseSettings)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Database pool settings (for PostgreSQL)
DATABASE_POOL_SIZE = int(os.environ.get('DATABASE_POOL_SIZE', 5))
DATABASE_MAX_OVERFLOW = int(os.environ.get('DATABASE_MAX_OVERFLOW', 10))

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
}

# CORS configuration (mirrors FastAPI's security.cors_origins)
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8080',
]

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Security settings (mirrors FastAPI's BaseSecuritySettings)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 30)
)

# Git settings (mirrors FastAPI's BaseGitSettings)
GIT_TIMEOUT = int(os.environ.get('GIT_TIMEOUT', 300))
GIT_SSH_KEY_SIZE = int(os.environ.get('SSH_KEY_SIZE', 2048))
GIT_ALLOWED_HOSTS = ['github.com', 'gitlab.com', 'bitbucket.org']
GIT_ALLOW_ANY_HOST = False

# Pipeline settings (mirrors FastAPI's BasePipelineSettings)
PIPELINE_BUILD_TIMEOUT = int(os.environ.get('BUILD_TIMEOUT', 1800))
PIPELINE_MAX_CONCURRENT_BUILDS = int(os.environ.get('MAX_CONCURRENT_BUILDS', 3))
PIPELINE_WORKSPACE_DIR = os.environ.get('WORKSPACE_DIR', '/tmp/open_webui_builds')
PIPELINE_DEFAULT_RETENTION_DAYS = int(os.environ.get('DEFAULT_RETENTION_DAYS', 7))

# Registry settings (mirrors FastAPI's BaseRegistrySettings)
REGISTRY_TIMEOUT = int(os.environ.get('REGISTRY_TIMEOUT', 600))
DOCKER_API_VERSION = os.environ.get('DOCKER_API_VERSION', 'auto')
DOCKER_BASE_URL = os.environ.get('DOCKER_BASE_URL', 'unix://var/run/docker.sock')

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'apps.core.logging.JSONFormatter',
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# API Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'Open WebUI Customizer API',
    'DESCRIPTION': 'API for customizing Open WebUI with custom branding and builds',
    'VERSION': '1.0.0',
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'