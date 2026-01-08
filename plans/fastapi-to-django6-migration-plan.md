# FastAPI to Django 6 Migration Plan

## Overview

This document outlines the comprehensive migration strategy for converting the **Open WebUI Customizer** application from FastAPI to Django 6 framework. The migration will create a new Django project in a completely separate directory, preserving all existing FastAPI code for reference and parallel operation during the transition.

**Migration Type:** Full framework migration (FastAPI → Django 6)  
**Approach:** Greenfield Django project with component-by-component migration  
**Preservation:** Original FastAPI project remains untouched

---

## Table of Contents

1. [Current Project Analysis](#1-current-project-analysis)
2. [Django 6 Project Structure](#2-django-6-project-structure)
3. [Component Migration Mapping](#3-component-migration-mapping)
4. [Phase 1: Project Setup and Configuration](#4-phase-1-project-setup-and-configuration)
5. [Phase 2: Models Migration](#5-phase-2-models-migration)
6. [Phase 3: API Endpoints Migration](#6-phase-3-api-endpoints-migration)
7. [Phase 4: Services Migration](#7-phase-4-services-migration)
8. [Phase 5: Templates, Static Files, and HTMX Integration](#8-phase-5-templates-static-files-and-htmx-integration)
9. [Phase 6: Testing Migration](#9-phase-6-testing-migration)
10. [Phase 7: DevOps and Deployment](#10-phase-7-devops-and-deployment)
11. [Migration Execution Checklist](#11-migration-execution-checklist)
12. [Risk Assessment and Mitigation](#12-risk-assessment-and-mitigation)
13. [Rollback Strategy](#13-rollback-strategy)

---

## 1. Current Project Analysis

### 1.1 FastAPI Project Structure

```
open-webui-customizer/
├── app/
│   ├── main.py                    # FastAPI app initialization
│   ├── exceptions.py              # Exception exports
│   ├── alembic.ini                # Alembic configuration
│   ├── alembic/                   # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── api/                       # API route handlers
│   │   ├── __init__.py
│   │   ├── assets.py
│   │   ├── branding.py
│   │   ├── configuration.py
│   │   ├── credential.py
│   │   ├── credentials.py
│   │   ├── dashboard.py
│   │   ├── enhanced_pipeline.py
│   │   ├── git_repository.py
│   │   ├── pipeline.py
│   │   ├── registry.py
│   │   ├── router.py
│   │   ├── templates.py
│   │   └── views.py
│   ├── config/                    # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py            # Pydantic tiered settings
│   ├── exceptions/                # Custom exceptions
│   │   ├── __init__.py
│   │   └── base.py
│   ├── models/                    # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── models.py
│   ├── schemas/                   # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── branding.py
│   │   ├── configuration.py
│   │   ├── credentials.py
│   │   ├── pipeline.py
│   │   └── registry.py
│   ├── services/                  # Business logic services
│   │   ├── __init__.py
│   │   ├── asset_service.py
│   │   ├── branding_application_service.py
│   │   ├── branding.py
│   │   ├── configuration.py
│   │   ├── credential_service.py
│   │   ├── dashboard_service.py
│   │   ├── encryption_service.py
│   │   ├── enhanced_pipeline_service.py
│   │   ├── git_repository_service.py
│   │   ├── git_service.py
│   │   ├── pipeline_service.py
│   │   ├── pipeline.py
│   │   ├── registry_service.py
│   │   ├── registry.py
│   │   ├── template_service.py
│   │   └── validation_service.py
│   ├── static/                    # Static assets
│   │   ├── script.js
│   │   ├── style.css
│   │   ├── css/
│   │   └── js/
│   ├── templates/                 # Jinja2 templates
│   │   └── *.html
│   └── utils/                     # Utility modules
│       ├── __init__.py
│       ├── logging.py
│       └── validators.py
├── tests/                         # Test suite
├── alembic/                       # Root-level migrations
├── customization/                 # User customization files
├── docs/                          # Documentation
├── plans/                         # Planning documents
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container configuration
├── Makefile                       # Build automation
└── .env.example                   # Environment template
```

### 1.2 Current Technology Stack

| Component | Current (FastAPI) | Target (Django 6) |
|-----------|-------------------|-------------------|
| Web Framework | FastAPI 0.104+ | Django 6.0+ |
| ORM | SQLAlchemy 2.0 | Django ORM |
| Database Migrations | Alembic | Django Migrations |
| Data Validation | Pydantic 2.5+ | Django Forms / DRF Serializers |
| Templates | Jinja2 | Django Templates |
| API Documentation | OpenAPI (auto) | DRF Spectacular / drf-yasg |
| ASGI Server | Uvicorn | Uvicorn / Daphne |
| Authentication | python-jose | Django Auth / SimpleJWT |
| CORS | FastAPI CORSMiddleware | django-cors-headers |

### 1.3 Database Models Summary

| Model | Description | Relationships |
|-------|-------------|---------------|
| `BrandingTemplate` | Branding configuration templates | Has many BrandingAsset |
| `BrandingAsset` | Individual branding files | Belongs to BrandingTemplate |
| `ContainerRegistry` | Docker registry configurations | Referenced by PipelineRun |
| `Configuration` | Key-value configuration store | None |
| `PipelineRun` | Build pipeline executions | Has GitRepository, BuildOutputs |
| `Credential` | Encrypted credential storage | Referenced by GitRepository |
| `GitRepository` | Git repository configurations | Has Credential, PipelineRuns |
| `BuildOutput` | Build artifacts tracking | Belongs to PipelineRun |

---

## 2. Django 6 Project Structure

### 2.1 Recommended Django Project Layout

```
open-webui-customizer-django/
├── manage.py                      # Django CLI
├── config/                        # Project configuration
│   ├── __init__.py
│   ├── settings/                  # Tiered settings
│   │   ├── __init__.py
│   │   ├── base.py                # Base settings
│   │   ├── development.py         # Development overrides
│   │   ├── staging.py             # Staging overrides
│   │   └── production.py          # Production overrides
│   ├── urls.py                    # Root URL configuration
│   ├── asgi.py                    # ASGI application
│   └── wsgi.py                    # WSGI application
├── apps/                          # Django applications
│   ├── __init__.py
│   ├── core/                      # Core app (shared utilities)
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   ├── utils.py
│   │   └── validators.py
│   ├── branding/                  # Branding management app
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── serializers.py
│   │   │   └── views.py
│   │   ├── migrations/
│   │   ├── templates/
│   │   │   └── branding/
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_models.py
│   │       ├── test_views.py
│   │       └── test_services.py
│   ├── credentials/               # Credentials management app
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── encryption.py
│   │   ├── urls.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── serializers.py
│   │   │   └── views.py
│   │   ├── migrations/
│   │   └── tests/
│   ├── pipelines/                 # Pipeline execution app
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── tasks.py               # Celery tasks
│   │   ├── urls.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── serializers.py
│   │   │   └── views.py
│   │   ├── migrations/
│   │   ├── templates/
│   │   │   └── pipelines/
│   │   └── tests/
│   ├── registries/                # Container registry app
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── serializers.py
│   │   │   └── views.py
│   │   ├── migrations/
│   │   └── tests/
│   ├── repositories/              # Git repositories app
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── serializers.py
│   │   │   └── views.py
│   │   ├── migrations/
│   │   └── tests/
│   └── dashboard/                 # Dashboard and UI app
│       ├── __init__.py
│       ├── apps.py
│       ├── urls.py
│       ├── views.py
│       ├── templates/
│       │   └── dashboard/
│       └── tests/
├── static/                        # Project-level static files
│   ├── css/
│   ├── js/
│   └── images/
├── templates/                     # Project-level templates
│   ├── base.html
│   └── components/
├── media/                         # User-uploaded files
│   └── customization/
├── tests/                         # Integration tests
│   ├── __init__.py
│   ├── conftest.py
│   └── test_integration.py
├── requirements/                  # Split requirements
│   ├── base.txt
│   ├── development.txt
│   ├── staging.txt
│   └── production.txt
├── docker/                        # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
├── scripts/                       # Utility scripts
│   ├── migrate_data.py
│   └── setup_dev.sh
├── .env.example
├── pyproject.toml                 # Modern Python packaging
├── Makefile
└── README.md
```

---

## 3. Component Migration Mapping

### 3.1 File-by-File Migration Map

| FastAPI Component | Django Equivalent | Migration Notes |
|-------------------|-------------------|-----------------|
| `app/main.py` | `config/urls.py`, `config/asgi.py` | Split into URL config and ASGI setup |
| `app/api/*.py` | `apps/*/api/views.py` | Convert to DRF ViewSets/APIViews |
| `app/models/models.py` | `apps/*/models.py` | Convert SQLAlchemy to Django ORM |
| `app/models/database.py` | `config/settings/base.py` | Database config in Django settings |
| `app/schemas/*.py` | `apps/*/api/serializers.py` | Convert Pydantic to DRF Serializers |
| `app/services/*.py` | `apps/*/services.py` | Keep service layer, adapt to Django |
| `app/config/settings.py` | `config/settings/*.py` | Convert Pydantic to Django settings |
| `app/exceptions/base.py` | `apps/core/exceptions.py` | Adapt to DRF exception handling |
| `app/utils/logging.py` | `apps/core/logging.py` | Integrate with Django logging |
| `app/templates/*.html` | `apps/*/templates/` | Minor syntax adjustments |
| `alembic/` | `apps/*/migrations/` | Recreate migrations with Django |

### 3.2 API Endpoint Migration Map

| FastAPI Route | HTTP Method | Django URL Pattern | DRF View |
|---------------|-------------|--------------------|----|
| `/api/v1/branding/templates` | GET | `/api/v1/branding/templates/` | `BrandingTemplateViewSet.list` |
| `/api/v1/branding/templates` | POST | `/api/v1/branding/templates/` | `BrandingTemplateViewSet.create` |
| `/api/v1/branding/templates/{id}` | GET | `/api/v1/branding/templates/<int:pk>/` | `BrandingTemplateViewSet.retrieve` |
| `/api/v1/branding/templates/{id}` | PUT | `/api/v1/branding/templates/<int:pk>/` | `BrandingTemplateViewSet.update` |
| `/api/v1/branding/templates/{id}` | DELETE | `/api/v1/branding/templates/<int:pk>/` | `BrandingTemplateViewSet.destroy` |
| `/api/v1/branding/upload` | POST | `/api/v1/branding/upload/` | `BrandingAssetUploadView` |
| `/api/v1/credentials/` | GET, POST | `/api/v1/credentials/` | `CredentialViewSet` |
| `/api/v1/credentials/{id}` | GET, PUT, DELETE | `/api/v1/credentials/<int:pk>/` | `CredentialViewSet` |
| `/api/v1/credentials/{id}/verify` | POST | `/api/v1/credentials/<int:pk>/verify/` | `CredentialViewSet.verify` |
| `/api/v1/pipeline/runs` | GET, POST | `/api/v1/pipelines/runs/` | `PipelineRunViewSet` |
| `/api/v1/registries/` | GET, POST | `/api/v1/registries/` | `RegistryViewSet` |
| `/api/v1/repositories/` | GET, POST | `/api/v1/repositories/` | `GitRepositoryViewSet` |

---

## 4. Phase 1: Project Setup and Configuration

### 4.1 Initialize Django Project

```bash
# Create new project directory
mkdir open-webui-customizer-django
cd open-webui-customizer-django

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install Django 6 and dependencies
pip install Django>=6.0 djangorestframework django-cors-headers

# Start Django project with custom structure
django-admin startproject config .
```

### 4.2 Create Django Applications

```bash
# Create apps directory
mkdir -p apps

# Create individual apps
python manage.py startapp core apps/core
python manage.py startapp branding apps/branding
python manage.py startapp credentials apps/credentials
python manage.py startapp pipelines apps/pipelines
python manage.py startapp registries apps/registries
python manage.py startapp repositories apps/repositories
python manage.py startapp dashboard apps/dashboard
```

### 4.3 Base Settings Configuration

**File: `config/settings/base.py`**

```python
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
    
    # Local apps
    'apps.core',
    'apps.branding',
    'apps.credentials',
    'apps.pipelines',
    'apps.registries',
    'apps.repositories',
    'apps.dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
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
```

### 4.4 Development Settings

**File: `config/settings/development.py`**

```python
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
```

### 4.5 Production Settings

**File: `config/settings/production.py`**

```python
"""
Production settings - mirrors FastAPI's ProductionSettings.
"""

from .base import *

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Production database (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
    }
}

# Security requirements
SECRET_KEY = os.environ['SECRET_KEY']  # Required
ENCRYPTION_KEY = os.environ['ENCRYPTION_KEY']  # Required

# CORS - Specific origins only
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### 4.6 Requirements Files

**File: `requirements/base.txt`**

```text
# Django 6 Core
Django>=6.0,<7.0

# Django REST Framework
djangorestframework>=3.15.0
drf-spectacular>=0.27.0

# Database
psycopg2-binary>=2.9.0

# Security and encryption
cryptography>=42.0.0
PyJWT>=2.8.0

# CORS
django-cors-headers>=4.3.0

# Git operations
gitpython>=3.1.0

# Docker integration
docker>=7.0.0

# SSH operations
paramiko>=3.4.0

# HTTP client
httpx>=0.27.0

# File handling
aiofiles>=23.2.0

# Background tasks
celery>=5.3.0
redis>=5.0.0

# Monitoring
prometheus-client>=0.19.0

# Utilities
python-dateutil>=2.8.0
python-dotenv>=1.0.0
```

**File: `requirements/development.txt`**

```text
-r base.txt

# Testing
pytest>=8.0.0
pytest-django>=4.8.0
pytest-cov>=4.1.0
pytest-asyncio>=0.23.0
factory-boy>=3.3.0

# Code quality
black>=24.0.0
isort>=5.13.0
flake8>=7.0.0
mypy>=1.8.0
ruff>=0.2.0
pre-commit>=3.6.0

# Debugging
django-debug-toolbar>=4.3.0
ipython>=8.0.0

# Type stubs
django-stubs>=4.2.0
djangorestframework-stubs>=3.14.0
```

---

## 5. Phase 2: Models Migration

### 5.1 Model Conversion Strategy

Convert SQLAlchemy models to Django ORM models. The following table shows the field type mappings:

| SQLAlchemy Type | Django ORM Type |
|-----------------|-----------------|
| `Column(Integer, primary_key=True)` | `AutoField(primary_key=True)` or `BigAutoField` |
| `Column(String)` | `CharField(max_length=N)` |
| `Column(String, unique=True)` | `CharField(max_length=N, unique=True)` |
| `Column(Text)` | `TextField()` |
| `Column(DateTime)` | `DateTimeField()` |
| `Column(Boolean)` | `BooleanField()` |
| `Column(JSON)` | `JSONField()` |
| `Column(Integer, ForeignKey(...))` | `ForeignKey(..., on_delete=...)` |
| `relationship(...)` | `ForeignKey` or `ManyToManyField` |

### 5.2 Branding Models

**File: `apps/branding/models.py`**

```python
"""
Django models for branding management.
Converted from app/models/models.py BrandingTemplate and BrandingAsset.
"""

from django.db import models
from django.utils import timezone


class BrandingTemplate(models.Model):
    """
    Branding configuration templates.
    Equivalent to FastAPI's BrandingTemplate SQLAlchemy model.
    """
    
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    brand_name = models.CharField(max_length=255, blank=True, null=True)
    replacement_rules = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'branding_templates'
        ordering = ['-created_at']
        verbose_name = 'Branding Template'
        verbose_name_plural = 'Branding Templates'
    
    def __str__(self):
        return self.name


class BrandingAsset(models.Model):
    """
    Individual branding files associated with a template.
    Equivalent to FastAPI's BrandingAsset SQLAlchemy model.
    """
    
    template = models.ForeignKey(
        BrandingTemplate,
        on_delete=models.CASCADE,
        related_name='assets'
    )
    file_name = models.CharField(max_length=255, db_index=True)
    file_type = models.CharField(max_length=50)  # logo, favicon, theme, etc.
    file_path = models.CharField(max_length=1024)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'branding_assets'
        ordering = ['-created_at']
        verbose_name = 'Branding Asset'
        verbose_name_plural = 'Branding Assets'
        unique_together = ['template', 'file_name']
    
    def __str__(self):
        return f"{self.template.name} - {self.file_name}"
```

### 5.3 Credentials Models

**File: `apps/credentials/models.py`**

```python
"""
Django models for credential management.
Converted from app/models/models.py Credential.
"""

from django.db import models
from django.utils import timezone


class Credential(models.Model):
    """
    Stores encrypted credentials for various services.
    Equivalent to FastAPI's Credential SQLAlchemy model.
    """
    
    CREDENTIAL_TYPES = [
        ('git_ssh', 'Git SSH'),
        ('git_https', 'Git HTTPS'),
        ('registry_docker_hub', 'Docker Hub Registry'),
        ('registry_aws_ecr', 'AWS ECR Registry'),
        ('registry_quay_io', 'Quay.io Registry'),
        ('registry_generic', 'Generic Registry'),
    ]
    
    name = models.CharField(max_length=255, unique=True, db_index=True)
    credential_type = models.CharField(
        max_length=50, 
        choices=CREDENTIAL_TYPES, 
        db_index=True
    )
    encrypted_data = models.TextField()  # JSON string with encrypted payload
    encryption_key_id = models.CharField(max_length=255, blank=True, null=True)
    metadata = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    last_used_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'credentials'
        ordering = ['-created_at']
        verbose_name = 'Credential'
        verbose_name_plural = 'Credentials'
    
    def __str__(self):
        return f"{self.name} ({self.get_credential_type_display()})"
    
    @property
    def is_expired(self):
        """Check if credential has expired."""
        if self.expires_at:
            return self.expires_at < timezone.now()
        return False
```

### 5.4 Pipeline Models

**File: `apps/pipelines/models.py`**

```python
"""
Django models for pipeline management.
Converted from app/models/models.py PipelineRun and BuildOutput.
"""

from django.db import models
from django.utils import timezone


class PipelineRun(models.Model):
    """
    Pipeline execution records.
    Equivalent to FastAPI's PipelineRun SQLAlchemy model.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    OUTPUT_TYPE_CHOICES = [
        ('zip', 'ZIP Archive'),
        ('docker_image', 'Docker Image'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    steps_to_execute = models.JSONField(default=list)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)
    logs = models.TextField(blank=True, null=True)
    
    # Custom fork support
    git_repository = models.ForeignKey(
        'repositories.GitRepository',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='pipeline_runs'
    )
    output_type = models.CharField(
        max_length=20,
        choices=OUTPUT_TYPE_CHOICES,
        default='docker_image'
    )
    registry = models.ForeignKey(
        'registries.ContainerRegistry',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='pipeline_runs'
    )
    
    class Meta:
        db_table = 'pipeline_runs'
        ordering = ['-started_at']
        verbose_name = 'Pipeline Run'
        verbose_name_plural = 'Pipeline Runs'
    
    def __str__(self):
        return f"Pipeline Run #{self.pk} - {self.status}"


class BuildOutput(models.Model):
    """
    Tracks generated build artifacts.
    Equivalent to FastAPI's BuildOutput SQLAlchemy model.
    """
    
    OUTPUT_TYPE_CHOICES = [
        ('zip', 'ZIP Archive'),
        ('docker_image', 'Docker Image'),
    ]
    
    pipeline_run = models.ForeignKey(
        PipelineRun,
        on_delete=models.CASCADE,
        related_name='build_outputs'
    )
    output_type = models.CharField(max_length=50, choices=OUTPUT_TYPE_CHOICES)
    file_path = models.CharField(max_length=1024, blank=True, null=True)
    image_url = models.CharField(max_length=1024, blank=True, null=True)
    file_size_bytes = models.BigIntegerField(blank=True, null=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True, null=True)
    download_count = models.IntegerField(default=0)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'build_outputs'
        ordering = ['-created_at']
        verbose_name = 'Build Output'
        verbose_name_plural = 'Build Outputs'
    
    def __str__(self):
        return f"Build Output #{self.pk} - {self.output_type}"
```

### 5.5 Repository Models

**File: `apps/repositories/models.py`**

```python
"""
Django models for Git repository management.
Converted from app/models/models.py GitRepository.
"""

from django.db import models
from django.utils import timezone


class GitRepository(models.Model):
    """
    Configured Git repositories for building custom forks.
    Equivalent to FastAPI's GitRepository SQLAlchemy model.
    """
    
    REPOSITORY_TYPE_CHOICES = [
        ('https', 'HTTPS'),
        ('ssh', 'SSH'),
    ]
    
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    ]
    
    name = models.CharField(max_length=255, unique=True, db_index=True)
    repository_url = models.CharField(max_length=1024)
    repository_type = models.CharField(
        max_length=20,
        choices=REPOSITORY_TYPE_CHOICES
    )
    default_branch = models.CharField(max_length=255, default='main')
    credential = models.ForeignKey(
        'credentials.Credential',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='git_repositories'
    )
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=50,
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending'
    )
    verification_message = models.TextField(blank=True, null=True)
    is_experimental = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'git_repositories'
        ordering = ['-created_at']
        verbose_name = 'Git Repository'
        verbose_name_plural = 'Git Repositories'
    
    def __str__(self):
        return f"{self.name} ({self.repository_url})"
```

### 5.6 Registry Models

**File: `apps/registries/models.py`**

```python
"""
Django models for container registry management.
Converted from app/models/models.py ContainerRegistry.
"""

from django.db import models
from django.utils import timezone


class ContainerRegistry(models.Model):
    """
    Docker registry configurations.
    Equivalent to FastAPI's ContainerRegistry SQLAlchemy model.
    """
    
    REGISTRY_TYPE_CHOICES = [
        ('aws_ecr', 'AWS ECR'),
        ('docker_hub', 'Docker Hub'),
        ('quay_io', 'Quay.io'),
        ('generic', 'Generic Registry'),
    ]
    
    name = models.CharField(max_length=255, unique=True, db_index=True)
    registry_type = models.CharField(max_length=50, choices=REGISTRY_TYPE_CHOICES)
    base_image = models.CharField(max_length=512, blank=True, null=True)
    target_image = models.CharField(max_length=512, blank=True, null=True)
    aws_account_id = models.CharField(max_length=20, blank=True, null=True)
    aws_region = models.CharField(max_length=50, blank=True, null=True)
    repository_name = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)  # Encrypted
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'container_registries'
        ordering = ['-created_at']
        verbose_name = 'Container Registry'
        verbose_name_plural = 'Container Registries'
    
    def __str__(self):
        return f"{self.name} ({self.get_registry_type_display()})"
```

---

## 6. Phase 3: API Endpoints Migration

### 6.1 DRF Serializer Conversion

Convert Pydantic schemas to DRF serializers:

**File: `apps/credentials/api/serializers.py`**

```python
"""
DRF Serializers for credential management.
Converted from app/schemas/credentials.py.
"""

from rest_framework import serializers
from django.utils import timezone
from apps.credentials.models import Credential


class CredentialTypeSerializer(serializers.Serializer):
    """Schema describing credential type and its fields."""
    
    type = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    required_fields = serializers.ListField(child=serializers.CharField())
    optional_fields = serializers.ListField(child=serializers.CharField())


class CredentialCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating credentials.
    Equivalent to FastAPI's CredentialCreate Pydantic schema.
    """
    
    credential_data = serializers.JSONField(write_only=True)
    
    class Meta:
        model = Credential
        fields = [
            'name', 'credential_type', 'credential_data',
            'metadata', 'expires_at'
        ]
    
    def validate_credential_data(self, value):
        """Validate credential data based on type."""
        credential_type = self.initial_data.get('credential_type')
        
        required_fields = {
            'git_ssh': ['private_key'],
            'git_https': ['username', 'password_or_token'],
            'registry_docker_hub': ['username', 'access_token'],
            'registry_aws_ecr': ['aws_access_key_id', 'aws_secret_access_key'],
            'registry_quay_io': ['username', 'password'],
            'registry_generic': ['username', 'password_or_token'],
        }
        
        if credential_type in required_fields:
            missing = [f for f in required_fields[credential_type] if f not in value]
            if missing:
                raise serializers.ValidationError(
                    f"Missing required fields: {missing}"
                )
        
        return value
    
    def validate_expires_at(self, value):
        """Ensure expiration is in the future."""
        if value and value < timezone.now():
            raise serializers.ValidationError(
                "Expiration date cannot be in the past"
            )
        return value


class CredentialResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for credential responses (without sensitive data).
    Equivalent to FastAPI's CredentialResponse schema.
    """
    
    class Meta:
        model = Credential
        fields = [
            'id', 'name', 'credential_type', 'metadata',
            'is_active', 'created_at', 'updated_at',
            'expires_at', 'last_used_at'
        ]
        read_only_fields = fields


class CredentialDetailSerializer(CredentialResponseSerializer):
    """Extended serializer with computed fields."""
    
    credential_type_name = serializers.SerializerMethodField()
    has_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    
    class Meta(CredentialResponseSerializer.Meta):
        fields = CredentialResponseSerializer.Meta.fields + [
            'credential_type_name', 'has_expired', 'days_until_expiry'
        ]
    
    def get_credential_type_name(self, obj):
        return obj.get_credential_type_display()
    
    def get_has_expired(self, obj):
        return obj.is_expired
    
    def get_days_until_expiry(self, obj):
        if obj.expires_at:
            delta = obj.expires_at - timezone.now()
            return max(0, delta.days)
        return None


class CredentialUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating credential metadata."""
    
    class Meta:
        model = Credential
        fields = ['name', 'metadata', 'expires_at']
        extra_kwargs = {
            'name': {'required': False},
            'metadata': {'required': False},
            'expires_at': {'required': False},
        }


class CredentialVerificationResultSerializer(serializers.Serializer):
    """Serializer for verification results."""
    
    credential_id = serializers.IntegerField()
    valid = serializers.BooleanField()
    message = serializers.CharField()
    error_details = serializers.CharField(required=False, allow_null=True)
    verification_time = serializers.DateTimeField()
```

### 6.2 DRF ViewSet Implementation

**File: `apps/credentials/api/views.py`**

```python
"""
DRF Views for credential management.
Converted from app/api/credentials.py.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from apps.credentials.models import Credential
from apps.credentials.services import CredentialService
from apps.credentials.api.serializers import (
    CredentialCreateSerializer,
    CredentialResponseSerializer,
    CredentialDetailSerializer,
    CredentialUpdateSerializer,
    CredentialVerificationResultSerializer,
    CredentialTypeSerializer,
)
from apps.core.exceptions import ValidationError, NotFoundError


class CredentialViewSet(viewsets.ModelViewSet):
    """
    ViewSet for credential CRUD operations.
    Equivalent to FastAPI's /api/v1/credentials/ router.
    """
    
    queryset = Credential.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CredentialCreateSerializer
        elif self.action == 'retrieve':
            return CredentialDetailSerializer
        elif self.action in ['update', 'partial_update']:
            return CredentialUpdateSerializer
        return CredentialResponseSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by type if specified
        credential_type = self.request.query_params.get('credential_type')
        if credential_type:
            queryset = queryset.filter(credential_type=credential_type)
        
        # Include expired if requested
        include_expired = self.request.query_params.get('include_expired', 'false')
        if include_expired.lower() != 'true':
            queryset = queryset.filter(
                models.Q(expires_at__isnull=True) |
                models.Q(expires_at__gt=timezone.now())
            )
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create a new credential with encrypted storage."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = CredentialService()
        credential = service.create_credential(serializer.validated_data)
        
        response_serializer = CredentialResponseSerializer(credential)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """Delete or deactivate a credential."""
        permanent = request.query_params.get('permanent', 'false').lower() == 'true'
        
        instance = self.get_object()
        service = CredentialService()
        service.delete_credential(instance.id, permanent=permanent)
        
        action_msg = "permanently deleted" if permanent else "deactivated"
        return Response(
            {"message": f"Credential {instance.id} {action_msg} successfully"},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify credential validity."""
        credential = self.get_object()
        service = CredentialService()
        
        is_valid, message = service.verify_credential(credential.id)
        
        result = {
            'credential_id': credential.id,
            'valid': is_valid,
            'message': message,
            'verification_time': timezone.now()
        }
        
        serializer = CredentialVerificationResultSerializer(result)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='types/info')
    def types_info(self, request):
        """Get information about credential types."""
        types_info = CredentialService.get_credential_type_descriptions()
        serializer = CredentialTypeSerializer(types_info, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='cleanup-expired')
    def cleanup_expired(self, request):
        """Deactivate expired credentials."""
        service = CredentialService()
        count = service.cleanup_expired_credentials()
        
        return Response({
            "message": f"Successfully deactivated {count} expired credentials",
            "count": count
        })
```

### 6.3 URL Configuration

**File: `apps/credentials/urls.py`**

```python
"""URL configuration for credentials app."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.credentials.api.views import CredentialViewSet

router = DefaultRouter()
router.register(r'', CredentialViewSet, basename='credential')

urlpatterns = [
    path('', include(router.urls)),
]
```

**File: `config/urls.py`**

```python
"""
Root URL configuration.
Equivalent to FastAPI's app.include_router() calls.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API v1 endpoints
    path('api/v1/branding/', include('apps.branding.urls')),
    path('api/v1/credentials/', include('apps.credentials.urls')),
    path('api/v1/pipelines/', include('apps.pipelines.urls')),
    path('api/v1/registries/', include('apps.registries.urls')),
    path('api/v1/repositories/', include('apps.repositories.urls')),
    
    # Dashboard and UI
    path('', include('apps.dashboard.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## 7. Phase 4: Services Migration

### 7.1 Service Layer Migration Strategy

The service layer can largely be preserved with minimal changes. Key adaptations:

1. Replace SQLAlchemy session with Django ORM
2. Replace Pydantic models with Django models/serializers
3. Adapt exception handling to DRF patterns

**File: `apps/credentials/services.py`**

```python
"""
Service layer for credential management.
Migrated from app/services/credential_service.py.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone

from apps.credentials.models import Credential
from apps.credentials.encryption import EncryptionService
from apps.core.exceptions import ValidationError, NotFoundError, DatabaseError
from apps.core.logging import get_logger

logger = get_logger(__name__)


class CredentialService:
    """
    Manages credential lifecycle with encryption and validation.
    Migrated from FastAPI's CredentialService.
    """
    
    def __init__(self):
        self.encryption_service = EncryptionService()
    
    @transaction.atomic
    def create_credential(self, data: Dict[str, Any]) -> Credential:
        """
        Create a new encrypted credential.
        
        Args:
            data: Validated credential data from serializer
            
        Returns:
            Created credential instance
        """
        # Check for duplicate names
        if Credential.objects.filter(name=data['name']).exists():
            raise ValidationError(
                f"Credential with name '{data['name']}' already exists"
            )
        
        # Encrypt sensitive data
        sensitive_data = json.dumps(data.pop('credential_data'))
        encrypted = self.encryption_service.encrypt(sensitive_data)
        
        # Create credential
        credential = Credential.objects.create(
            name=data['name'],
            credential_type=data['credential_type'],
            encrypted_data=json.dumps(encrypted),
            encryption_key_id=encrypted.get('key_id'),
            metadata=data.get('metadata', {}),
            expires_at=data.get('expires_at')
        )
        
        logger.info(f"Created credential '{credential.name}'", extra={
            'credential_id': credential.id,
            'credential_type': credential.credential_type
        })
        
        return credential
    
    def get_decrypted_credential(self, credential_id: int) -> Dict[str, Any]:
        """
        Retrieve and decrypt credential data.
        
        Args:
            credential_id: Database ID of the credential
            
        Returns:
            Decrypted credential data
        """
        try:
            credential = Credential.objects.get(id=credential_id)
        except Credential.DoesNotExist:
            raise NotFoundError(f"Credential with ID {credential_id} not found")
        
        if not credential.is_active:
            raise ValidationError("Credential is deactivated")
        
        if credential.is_expired:
            raise ValidationError("Credential has expired")
        
        # Decrypt
        encrypted_data = json.loads(credential.encrypted_data)
        decrypted = self.encryption_service.decrypt(encrypted_data)
        credential_data = json.loads(decrypted)
        
        # Update last used
        credential.last_used_at = timezone.now()
        credential.save(update_fields=['last_used_at'])
        
        return credential_data
    
    def verify_credential(self, credential_id: int) -> Tuple[bool, str]:
        """Verify credential validity."""
        try:
            data = self.get_decrypted_credential(credential_id)
            credential = Credential.objects.get(id=credential_id)
            
            # Type-specific validation
            if credential.credential_type == 'git_ssh':
                return True, "SSH key format appears valid"
            elif credential.credential_type == 'git_https':
                if data.get('username') and data.get('password_or_token'):
                    return True, f"HTTPS credential appears valid"
                return False, "Missing username or token"
            
            return True, f"Credential format valid"
            
        except (ValidationError, NotFoundError) as e:
            return False, str(e)
    
    def delete_credential(self, credential_id: int, permanent: bool = False) -> bool:
        """Delete or deactivate a credential."""
        try:
            credential = Credential.objects.get(id=credential_id)
        except Credential.DoesNotExist:
            return False
        
        if permanent:
            credential.delete()
            logger.warning(f"Permanently deleted credential {credential_id}")
        else:
            credential.is_active = False
            credential.save(update_fields=['is_active', 'updated_at'])
            logger.info(f"Deactivated credential {credential_id}")
        
        return True
    
    def cleanup_expired_credentials(self) -> int:
        """Deactivate all expired credentials."""
        count = Credential.objects.filter(
            is_active=True,
            expires_at__lt=timezone.now()
        ).update(is_active=False)
        
        logger.info(f"Deactivated {count} expired credentials")
        return count
    
    @staticmethod
    def get_credential_type_descriptions() -> List[Dict[str, Any]]:
        """Get descriptions of all credential types."""
        return [
            {
                'type': 'git_ssh',
                'name': 'Git SSH',
                'description': 'SSH key for Git repository access',
                'required_fields': ['private_key'],
                'optional_fields': ['passphrase', 'known_hosts'],
            },
            {
                'type': 'git_https',
                'name': 'Git HTTPS',
                'description': 'HTTPS credentials for Git repository',
                'required_fields': ['username', 'password_or_token'],
                'optional_fields': [],
            },
            # ... other types
        ]
```

---

## 8. Phase 5: Templates and Static Files

### 8.1 Template Migration

Django templates have minor syntax differences from Jinja2:

| Jinja2 | Django |
|--------|--------|
| `{{ url_for('static', filename='...') }}` | `{% static '...' %}` |
| `{% include 'file.html' %}` | `{% include 'file.html' %}` (same) |
| `{% block content %}{% endblock %}` | `{% block content %}{% endblock %}` (same) |
| `{{ request.path }}` | `{{ request.path }}` (same) |

**File: `templates/base.html`**

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Open WebUI Customizer{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'css/style.css' %}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <a href="{% url 'dashboard:index' %}" class="brand">Open WebUI Customizer</a>
            <ul class="nav-links">
                <li><a href="{% url 'dashboard:index' %}">Dashboard</a></li>
                <li><a href="{% url 'branding:list' %}">Branding</a></li>
                <li><a href="{% url 'pipelines:list' %}">Pipelines</a></li>
                <li><a href="{% url 'credentials:list' %}">Credentials</a></li>
            </ul>
        </div>
    </nav>
    
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    
    <script src="{% static 'js/script.js' %}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### 8.2 Static Files Migration

Copy static files from `app/static/` to `static/` in the Django project:

```bash
# From the Django project root
cp -r ../open-webui-customizer/app/static/* static/
```

---

## 9. Phase 6: Testing Migration

### 9.1 Test Framework Migration

| FastAPI (pytest) | Django (pytest-django) |
|------------------|------------------------|
| `TestClient` | `APIClient` |
| `@pytest.fixture` | `@pytest.fixture` (same) |
| `AsyncClient` | `AsyncClient` (DRF) |

### 9.2 Test Configuration

**File: `conftest.py`**

```python
"""
Pytest configuration for Django tests.
"""

import pytest
from rest_framework.test import APIClient
from django.test import override_settings


@pytest.fixture
def api_client():
    """Return DRF API client."""
    return APIClient()


@pytest.fixture
def credential_factory(db):
    """Factory for creating test credentials."""
    def _create_credential(**kwargs):
        from apps.credentials.models import Credential
        defaults = {
            'name': 'test-credential',
            'credential_type': 'git_https',
            'encrypted_data': '{}',
            'metadata': {},
        }
        defaults.update(kwargs)
        return Credential.objects.create(**defaults)
    return _create_credential
```

### 9.3 Test Example

**File: `apps/credentials/tests/test_api.py`**

```python
"""
API tests for credentials.
Migrated from FastAPI tests.
"""

import pytest
from rest_framework import status
from django.urls import reverse


@pytest.mark.django_db
class TestCredentialAPI:
    """Test credential API endpoints."""
    
    def test_create_credential(self, api_client):
        """Test creating a new credential."""
        url = reverse('credential-list')
        data = {
            'name': 'test-cred',
            'credential_type': 'git_https',
            'credential_data': {
                'username': 'testuser',
                'password_or_token': 'testtoken'
            }
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'test-cred'
    
    def test_list_credentials(self, api_client, credential_factory):
        """Test listing credentials."""
        credential_factory(name='cred-1')
        credential_factory(name='cred-2')
        
        url = reverse('credential-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
    
    def test_verify_credential(self, api_client, credential_factory):
        """Test credential verification."""
        credential = credential_factory()
        
        url = reverse('credential-verify', kwargs={'pk': credential.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'valid' in response.data
```

---

## 10. Phase 7: DevOps and Deployment

### 10.1 Docker Configuration

**File: `docker/Dockerfile`**

```dockerfile
# Django 6 Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/production.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "config.wsgi:application"]
```

### 10.2 Docker Compose

**File: `docker/docker-compose.yml`**

```yaml
version: '3.8'

services:
  web:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - DATABASE_URL=postgres://postgres:postgres@db:5432/customizer
      - SECRET_KEY=${SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - db
      - redis
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
  
  db:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=customizer
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
  
  celery:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: celery -A config worker -l info
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - DATABASE_URL=postgres://postgres:postgres@db:5432/customizer
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### 10.3 Database Migration Script

**File: `scripts/migrate_data.py`**

```python
#!/usr/bin/env python
"""
Data migration script from FastAPI SQLite to Django PostgreSQL.

Usage:
    python scripts/migrate_data.py --source sqlite:///./customizer.db
"""

import os
import sys
import argparse
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from sqlalchemy import create_engine, MetaData
from django.db import connection

def migrate_table(source_engine, table_name, django_model):
    """Migrate a single table from SQLAlchemy to Django."""
    metadata = MetaData()
    metadata.reflect(bind=source_engine)
    
    if table_name not in metadata.tables:
        print(f"Table {table_name} not found in source database")
        return 0
    
    source_table = metadata.tables[table_name]
    
    with source_engine.connect() as conn:
        rows = conn.execute(source_table.select()).fetchall()
    
    count = 0
    for row in rows:
        data = dict(row._mapping)
        # Remove auto-generated ID to let Django create new one
        # or preserve if needed
        django_model.objects.create(**data)
        count += 1
    
    print(f"Migrated {count} rows from {table_name}")
    return count

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, help='Source database URL')
    args = parser.parse_args()
    
    source_engine = create_engine(args.source)
    
    # Import Django models
    from apps.branding.models import BrandingTemplate, BrandingAsset
    from apps.credentials.models import Credential
    from apps.registries.models import ContainerRegistry
    from apps.repositories.models import GitRepository
    from apps.pipelines.models import PipelineRun, BuildOutput
    
    # Migrate each table
    migrate_table(source_engine, 'branding_templates', BrandingTemplate)
    migrate_table(source_engine, 'branding_assets', BrandingAsset)
    migrate_table(source_engine, 'credentials', Credential)
    migrate_table(source_engine, 'container_registries', ContainerRegistry)
    migrate_table(source_engine, 'git_repositories', GitRepository)
    migrate_table(source_engine, 'pipeline_runs', PipelineRun)
    migrate_table(source_engine, 'build_outputs', BuildOutput)
    
    print("Migration complete!")

if __name__ == '__main__':
    main()
```

---

## 11. Migration Execution Checklist

### Phase 1: Setup (Week 1)
- [ ] Create new Django project directory
- [ ] Initialize Django 6 project with proper structure
- [ ] Configure tiered settings (dev/staging/prod)
- [ ] Set up requirements files
- [ ] Configure logging and exceptions
- [ ] Set up pre-commit hooks and linting

### Phase 2: Models (Week 2)
- [ ] Create Django apps for each domain
- [ ] Convert all SQLAlchemy models to Django ORM
- [ ] Create and run initial migrations
- [ ] Set up admin interface for all models
- [ ] Write model unit tests

### Phase 3: API Endpoints (Week 3-4)
- [ ] Create DRF serializers for all schemas
- [ ] Implement ViewSets for all endpoints
- [ ] Configure URL routing
- [ ] Set up API documentation (drf-spectacular)
- [ ] Write API integration tests
- [ ] Verify API parity with FastAPI version

### Phase 4: Services (Week 5)
- [ ] Migrate credential service
- [ ] Migrate branding service
- [ ] Migrate pipeline service
- [ ] Migrate git repository service
- [ ] Migrate encryption service
- [ ] Write service unit tests

### Phase 5: Templates and UI (Week 6)
- [ ] Migrate all HTML templates
- [ ] Copy and organize static files
- [ ] Create Django template tags as needed
- [ ] Test all UI pages
- [ ] Verify JavaScript functionality

### Phase 6: Testing (Week 7)
- [ ] Configure pytest-django
- [ ] Migrate all existing tests
- [ ] Add missing test coverage
- [ ] Run full test suite
- [ ] Fix any failing tests

### Phase 7: DevOps (Week 8)
- [ ] Create Docker configuration
- [ ] Set up docker-compose
- [ ] Create data migration scripts
- [ ] Test deployment process
- [ ] Document deployment procedures

### Final Steps
- [ ] Run parallel testing (both apps)
- [ ] Migrate production data
- [ ] Switch production traffic
- [ ] Monitor for issues
- [ ] Decommission FastAPI app (after validation period)

---

## 12. Risk Assessment and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data loss during migration | High | Low | Full backups, staged migration, validation scripts |
| API breaking changes | High | Medium | Comprehensive API testing, version compatibility layer |
| Performance regression | Medium | Medium | Load testing, database query optimization |
| Missing functionality | Medium | Low | Feature parity checklist, extensive testing |
| Deployment failures | High | Low | Staged rollout, rollback procedures |
| Team unfamiliarity with Django | Medium | Medium | Training sessions, documentation |

---

## 13. Rollback Strategy

### Immediate Rollback (< 1 hour)
1. Switch load balancer back to FastAPI instance
2. Keep Django instance running for investigation
3. Review error logs and identify issues

### Data Rollback
1. Restore database from pre-migration backup
2. Re-sync any data created during Django operation
3. Validate data integrity

### Code Rollback
1. FastAPI codebase remains in original repository
2. Can redeploy FastAPI version at any time
3. No code changes required for rollback

---

## Appendix A: Django 6 New Features to Leverage

Django 6 introduces several features that can improve the application:

1. **Composite Primary Keys** - For complex relationships
2. **Improved JSON Field** - Better querying for metadata fields
3. **Async ORM** - For async views and background tasks
4. **Enhanced Admin** - Better admin interface options

---

## Appendix B: References

- [Django 6 Documentation](https://docs.djangoproject.com/en/6.0/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/)
- [FastAPI to Django Migration Guide](https://testdriven.io/blog/moving-from-flask-to-django/)

---

*Document Version: 1.0*  
*Created: January 2026*  
*Last Updated: January 2026*