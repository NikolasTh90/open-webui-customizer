"""
URL configuration for the Open WebUI Customizer Django project.

This module defines the main URL patterns for the application,
including API routes, admin interface, and static/media files.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# API documentation views (optional)
try:
    from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
    api_docs_available = True
except ImportError:
    api_docs_available = False

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),

    # Dashboard and main app
    path('', include('apps.dashboard.urls')),

    # Frontend views
    path('credentials/', include('apps.credentials.urls')),
    path('repositories/', include('apps.repositories.urls')),
    path('registries/', include('apps.registries.urls')),
    path('pipelines/', include('apps.pipelines.urls')),
    path('branding/', include('apps.branding.urls')),

    # API endpoints
    path('', include('apps.credentials.api.urls')),
    path('', include('apps.repositories.api.urls')),
    path('', include('apps.registries.api.urls')),
    path('', include('apps.pipelines.api.urls')),
    path('', include('apps.branding.api.urls')),

    # API documentation (if available)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
