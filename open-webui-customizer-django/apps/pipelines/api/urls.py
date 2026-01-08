"""
URL configuration for pipelines API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.pipelines.api.views import PipelineRunViewSet, BuildOutputViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'pipelines', PipelineRunViewSet)
router.register(r'outputs', BuildOutputViewSet)

# The API URLs are determined automatically by the router
urlpatterns = [
    path('api/v1/', include(router.urls)),
]