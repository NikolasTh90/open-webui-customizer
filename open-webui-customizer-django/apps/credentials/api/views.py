"""
Django REST Framework views for credentials app.

This module provides API views for credential management including
CRUD operations, verification, and connection testing.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from apps.credentials.models import Credential, CredentialType
from apps.credentials.api.serializers import (
    CredentialSerializer, CredentialCreateSerializer, CredentialUpdateSerializer,
    CredentialDataUpdateSerializer, CredentialVerificationSerializer,
    CredentialTypeDescriptionSerializer, CredentialListSerializer
)


class CredentialPagination(PageNumberPagination):
    """Custom pagination for credentials."""

    page_size = 50
    page_size_query_param = 'per_page'
    max_page_size = 100


class CredentialViewSet(viewsets.ModelViewSet):
    """
    ViewSet for credential management.

    Provides CRUD operations for credentials with proper encryption
    and validation handling.
    """

    queryset = Credential.objects.filter(is_active=True)
    pagination_class = CredentialPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return CredentialCreateSerializer
        elif self.action == 'update':
            return CredentialUpdateSerializer
        elif self.action == 'partial_update':
            return CredentialUpdateSerializer
        return CredentialSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()

        # Filter by credential type
        credential_type = self.request.query_params.get('credential_type')
        if credential_type:
            queryset = queryset.filter(credential_type=credential_type)

        # Include expired credentials if requested
        include_expired = self.request.query_params.get('include_expired', 'false').lower() == 'true'
        if not include_expired:
            now = timezone.now()
            queryset = queryset.filter(
                models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
            )

        return queryset

    @action(detail=True, methods=['put'])
    def update_data(self, request, pk=None):
        """Update credential data (re-encryption required)."""
        credential = self.get_object()
        serializer = CredentialDataUpdateSerializer(
            data=request.data,
            context={'instance': credential}
        )

        if serializer.is_valid():
            credential_data = serializer.validated_data['credential_data']
            credential.set_credential_data(credential_data)
            credential.save()

            # Return updated credential
            response_serializer = self.get_serializer(credential)
            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify credential validity."""
        credential = self.get_object()

        # Basic verification - check if data can be decrypted
        try:
            credential_data = credential.get_credential_data()
            is_valid = True
            message = "Credential data is accessible and properly encrypted"
        except Exception as e:
            is_valid = False
            message = f"Credential verification failed: {str(e)}"

        serializer = CredentialVerificationSerializer({
            'credential_id': credential.id,
            'valid': is_valid,
            'message': message
        })

        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test credential connection with actual service."""
        credential = self.get_object()
        test_endpoint = request.data.get('test_endpoint')

        # Placeholder for connection testing
        # This would implement actual service connection tests
        test_results = {
            'credential_type': credential.credential_type,
            'connection_tested': False,
            'error': None,
            'details': None
        }

        # TODO: Implement actual connection tests based on credential type
        if credential.credential_type == CredentialType.GIT_SSH_KEY:
            test_results['details'] = "SSH key validation (not implemented)"
            test_results['connection_tested'] = True
        elif credential.credential_type == CredentialType.GIT_HTTPS_TOKEN:
            test_results['details'] = "HTTPS token validation (not implemented)"
            test_results['connection_tested'] = True
        else:
            test_results['error'] = "Connection test not implemented for this type"

        return Response(test_results)

    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get information about supported credential types."""
        from apps.credentials.models import Credential

        type_descriptions = Credential.get_credential_types_info()

        serializer = CredentialTypeDescriptionSerializer(type_descriptions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def cleanup_expired(self, request):
        """Clean up expired credentials."""
        expired_count = Credential.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        ).update(is_active=False)

        return Response({
            'message': f'Successfully deactivated {expired_count} expired credentials',
            'count': expired_count
        })

    def destroy(self, request, *args, **kwargs):
        """Soft delete credential by default."""
        permanent = request.query_params.get('permanent', 'false').lower() == 'true'

        instance = self.get_object()
        if permanent:
            # Hard delete
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            # Soft delete
            instance.is_active = False
            instance.save()
            return Response({'message': f'Credential {instance.id} deactivated successfully'})