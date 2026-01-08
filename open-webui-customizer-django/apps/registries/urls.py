"""
URL configuration for registries app frontend views.
"""

from django.urls import path
from apps.registries import views

app_name = 'registries'

urlpatterns = [
    path('', views.ContainerRegistryListView.as_view(), name='list'),
    path('create/', views.ContainerRegistryCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ContainerRegistryDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.ContainerRegistryUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.registry_delete, name='delete'),
    path('<int:pk>/test-connection/', views.registry_test_connection, name='test_connection'),
]