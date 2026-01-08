"""
URL configuration for registries API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.registries.api.views import ContainerRegistryViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'registries', ContainerRegistryViewSet)

# The API URLs are determined automatically by the router
urlpatterns = [
    path('api/v1/', include(router.urls)),
]