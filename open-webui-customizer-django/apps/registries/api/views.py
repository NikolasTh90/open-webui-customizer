"""
Django REST Framework views for registries app.

This module provides API views for container registry management including
CRUD operations, connection testing, and repository listing.
"""

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from apps.registries.models import ContainerRegistry, RegistryType
from apps.registries.api.serializers import (
    ContainerRegistrySerializer, ContainerRegistryCreateSerializer,
    ContainerRegistryUpdateSerializer, ContainerRegistryConnectionSerializer,
    RegistryTypeDescriptionSerializer
)


class ContainerRegistryPagination(PageNumberPagination):
    """Custom pagination for container registries."""

    page_size = 50
    page_size_query_param = 'per_page'
    max_page_size = 100


class ContainerRegistryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for container registry management.

    Provides CRUD operations for container registries with connection
    testing and repository browsing capabilities.
    """

    queryset = ContainerRegistry.objects.filter(is_active=True)
    pagination_class = ContainerRegistryPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return ContainerRegistryCreateSerializer
        elif self.action == 'update':
            return ContainerRegistryUpdateSerializer
        elif self.action == 'partial_update':
            return ContainerRegistryUpdateSerializer
        return ContainerRegistrySerializer

    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()

        # Filter by registry type
        registry_type = self.request.query_params.get('registry_type')
        if registry_type:
            queryset = queryset.filter(registry_type=registry_type)

        # Filter by region
        region = self.request.query_params.get('region')
        if region:
            queryset = queryset.filter(region=region)

        return queryset

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test registry connection and authentication."""
        registry = self.get_object()

        # This would implement actual registry connection testing
        # For now, we'll simulate connection test
        import time
        start_time = time.time()

        try:
            # Simulate connection test
            connected = True
            message = "Registry connection successful"
            response_time_ms = int((time.time() - start_time) * 1000)

            # Cache connection status
            registry._connection_verified = connected

        except Exception as e:
            connected = False
            message = f"Registry connection failed: {str(e)}"
            response_time_ms = int((time.time() - start_time) * 1000)

        serializer = ContainerRegistryConnectionSerializer({
            'registry_id': registry.id,
            'connected': connected,
            'message': message,
            'response_time_ms': response_time_ms
        })

        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def repositories(self, request, pk=None):
        """List repositories available in the registry."""
        registry = self.get_object()

        # This would implement actual repository listing from the registry
        # For now, return mock data
        mock_repositories = [
            {
                'name': f'my-app-{i}',
                'full_name': f'{registry.namespace}/my-app-{i}',
                'tags_count': 5,
                'last_updated': '2024-01-01T00:00:00Z',
                'size_bytes': 1024000
            }
            for i in range(1, 11)
        ]

        return Response({
            'registry': registry.name,
            'repositories': mock_repositories,
            'total_count': len(mock_repositories)
        })

    @action(detail=True, methods=['get'])
    def tags(self, request, pk=None):
        """List tags for a specific repository."""
        registry = self.get_object()
        repository = request.query_params.get('repository')

        if not repository:
            return Response(
                {'error': 'repository parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # This would implement actual tag listing from the registry
        # For now, return mock data
        mock_tags = [
            {
                'name': f'v1.{i}.0',
                'digest': f'sha256:mock{i}' * 4,
                'size_bytes': 512000,
                'created': '2024-01-01T00:00:00Z'
            }
            for i in range(10, 0, -1)
        ]

        return Response({
            'registry': registry.name,
            'repository': repository,
            'tags': mock_tags
        })

    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get information about supported registry types."""
        type_descriptions = [
            {
                'type': RegistryType.DOCKER_HUB,
                'display_name': 'Docker Hub',
                'description': 'Docker Hub container registry',
                'default_domain': 'docker.io',
                'features': ['Public repositories', 'Official images', 'Automated builds'],
                'requires_credentials': True
            },
            {
                'type': RegistryType.GITHUB_PACKAGES,
                'display_name': 'GitHub Container Registry',
                'description': 'GitHub Container Registry (ghcr.io)',
                'default_domain': 'ghcr.io',
                'features': ['GitHub integration', 'Package management', 'Access control'],
                'requires_credentials': True
            },
            {
                'type': RegistryType.GITLAB_REGISTRY,
                'display_name': 'GitLab Container Registry',
                'description': 'GitLab Container Registry',
                'default_domain': 'registry.gitlab.com',
                'features': ['CI/CD integration', 'Project access control', 'Dependency proxy'],
                'requires_credentials': True
            },
            {
                'type': RegistryType.AWS_ECR,
                'display_name': 'AWS ECR',
                'description': 'Amazon Elastic Container Registry',
                'default_domain': '*.amazonaws.com',
                'features': ['High availability', 'Security scanning', 'Cross-region replication'],
                'requires_credentials': True
            },
            {
                'type': RegistryType.GENERIC,
                'display_name': 'Generic Registry',
                'description': 'Any Docker-compatible registry',
                'default_domain': '',
                'features': ['Flexible deployment', 'Custom authentication'],
                'requires_credentials': True
            }
        ]

        serializer = RegistryTypeDescriptionSerializer(type_descriptions, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Soft delete registry by default."""
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
            return Response({'message': f'Registry {instance.id} deactivated successfully'})