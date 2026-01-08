"""
URL configuration for credentials app frontend views.
"""

from django.urls import path
from apps.credentials import views

app_name = 'credentials'

urlpatterns = [
    path('', views.CredentialListView.as_view(), name='list'),
    path('create/', views.CredentialCreateView.as_view(), name='create'),
    path('<int:pk>/', views.CredentialDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.CredentialUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.credential_delete, name='delete'),
    path('<int:pk>/verify/', views.credential_verify, name='verify'),
    path('<int:pk>/test-connection/', views.credential_test_connection, name='test_connection'),
    path('<int:pk>/update-data/', views.update_credential_data, name='update_data'),
]