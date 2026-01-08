"""
URL configuration for dashboard app.
"""

from django.urls import path
from apps.dashboard import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('health/', views.health_check, name='health'),
    path('api/', views.api_root, name='api-root'),
]