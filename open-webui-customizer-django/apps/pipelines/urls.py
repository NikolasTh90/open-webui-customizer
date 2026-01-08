"""
URL configuration for pipelines app frontend views.
"""

from django.urls import path
from apps.pipelines import views

app_name = 'pipelines'

urlpatterns = [
    path('', views.PipelineRunListView.as_view(), name='list'),
    path('create/', views.PipelineRunCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PipelineRunDetailView.as_view(), name='detail'),
    path('<int:pk>/cancel/', views.pipeline_cancel, name='cancel'),
    path('<int:pk>/retry/', views.pipeline_retry, name='retry'),
]