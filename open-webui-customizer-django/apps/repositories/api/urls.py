"""
URL configuration for repositories API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.repositories.api.views import GitRepositoryViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'repositories', GitRepositoryViewSet)

# The API URLs are determined automatically by the router
urlpatterns = [
    path('api/v1/', include(router.urls)),
]