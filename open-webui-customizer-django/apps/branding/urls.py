"""
URL configuration for branding app frontend views.
"""

from django.urls import path
from apps.branding import views

app_name = 'branding'

urlpatterns = [
    path('', views.BrandingTemplateListView.as_view(), name='list'),
    path('create/', views.BrandingTemplateCreateView.as_view(), name='create'),
    path('<int:pk>/', views.BrandingTemplateDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.BrandingTemplateUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.branding_template_delete, name='delete'),
    path('<int:pk>/set-default/', views.set_default_template, name='set_default'),
    path('<int:pk>/duplicate/', views.duplicate_template, name='duplicate'),
]