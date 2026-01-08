"""
URL configuration for branding API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.branding.api.views import BrandingTemplateViewSet, BrandingAssetViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'templates', BrandingTemplateViewSet)
router.register(r'assets', BrandingAssetViewSet)

# The API URLs are determined automatically by the router
urlpatterns = [
    path('api/v1/', include(router.urls)),
]