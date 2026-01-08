"""
URL configuration for repositories app frontend views.
"""

from django.urls import path
from apps.repositories import views

app_name = 'repositories'

urlpatterns = [
    path('', views.GitRepositoryListView.as_view(), name='list'),
    path('create/', views.GitRepositoryCreateView.as_view(), name='create'),
    path('<int:pk>/', views.GitRepositoryDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.GitRepositoryUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.repository_delete, name='delete'),
    path('<int:pk>/verify/', views.repository_verify, name='verify'),
    path('<int:pk>/sync/', views.repository_sync, name='sync'),
]