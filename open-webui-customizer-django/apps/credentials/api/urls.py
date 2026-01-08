"""
URL configuration for credentials API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.credentials.api.views import CredentialViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'credentials', CredentialViewSet)

# The API URLs are determined automatically by the router
urlpatterns = [
    path('api/v1/', include(router.urls)),
]