"""
Django REST Framework views for repositories app.

This module provides API views for Git repository management including
CRUD operations, verification, and synchronization.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from apps.repositories.models import GitRepository, RepositoryType, VerificationStatus
from apps.repositories.api.serializers import (
    GitRepositorySerializer, GitRepositoryCreateSerializer, GitRepositoryUpdateSerializer,
    GitRepositoryVerificationSerializer, RepositoryTypeDescriptionSerializer
)


class GitRepositoryPagination(PageNumberPagination):
    """Custom pagination for repositories."""

    page_size = 50
    page_size_query_param = 'per_page'
    max_page_size = 100


class GitRepositoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Git repository management.

    Provides CRUD operations for repositories with verification
    and synchronization capabilities.
    """

    queryset = GitRepository.objects.filter(is_active=True)
    pagination_class = GitRepositoryPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return GitRepositoryCreateSerializer
        elif self.action == 'update':
            return GitRepositoryUpdateSerializer
        elif self.action == 'partial_update':
            return GitRepositoryUpdateSerializer
        return GitRepositorySerializer

    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()

        # Filter by repository type
        repository_type = self.request.query_params.get('repository_type')
        if repository_type:
            queryset = queryset.filter(repository_type=repository_type)

        # Filter by verification status
        verification_status = self.request.query_params.get('verification_status')
        if verification_status:
            queryset = queryset.filter(verification_status=verification_status)

        # Include experimental repositories if requested
        include_experimental = self.request.query_params.get('include_experimental', 'true').lower() == 'true'
        if not include_experimental:
            queryset = queryset.filter(is_experimental=False)

        # Include expired repositories if requested
        include_expired = self.request.query_params.get('include_expired', 'false').lower() == 'true'
        if not include_expired:
            from django.utils import timezone
            from datetime import timedelta
            expiry_date = timezone.now() - timedelta(days=90)
            queryset = queryset.filter(last_commit_date__gt=expiry_date)

        return queryset

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify repository accessibility and update metadata."""
        repository = self.get_object()

        # Placeholder for repository verification
        # This would implement actual Git repository verification
        try:
            # Simulate verification process
            verification_results = {
                'repository_id': repository.id,
                'verified': True,
                'message': 'Repository verification successful',
                'last_commit_hash': 'abc123def456',
                'last_commit_date': timezone.now()
            }

            # Update repository with verification results
            repository.is_verified = True
            repository.verification_status = VerificationStatus.VERIFIED
            repository.commit_hash = verification_results['last_commit_hash']
            repository.last_commit_date = verification_results['last_commit_date']
            repository.save()

        except Exception as e:
            verification_results = {
                'repository_id': repository.id,
                'verified': False,
                'message': f'Repository verification failed: {str(e)}',
                'last_commit_hash': None,
                'last_commit_date': None
            }

            repository.is_verified = False
            repository.verification_status = VerificationStatus.FAILED
            repository.save()

        serializer = GitRepositoryVerificationSerializer(verification_results)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Synchronize repository data with remote."""
        repository = self.get_object()

        # Placeholder for repository synchronization
        # This would implement actual Git repository sync
        try:
            # Simulate sync process
            sync_results = {
                'repository_id': repository.id,
                'synced': True,
                'message': 'Repository synchronized successfully',
                'new_commits': 5,
                'last_commit_hash': 'def789ghi012',
                'last_commit_date': timezone.now()
            }

            # Update repository with sync results
            repository.commit_hash = sync_results['last_commit_hash']
            repository.last_commit_date = sync_results['last_commit_date']
            repository.save()

        except Exception as e:
            sync_results = {
                'repository_id': repository.id,
                'synced': False,
                'message': f'Repository synchronization failed: {str(e)}',
                'new_commits': 0,
                'last_commit_hash': None,
                'last_commit_date': None
            }

        return Response(sync_results)

    @action(detail=True, methods=['get'])
    def branches(self, request, pk=None):
        """Get available branches for the repository."""
        repository = self.get_object()

        # Placeholder for branch listing
        # This would implement actual Git branch listing
        branches = [
            {'name': 'main', 'is_default': True, 'last_commit': 'abc123'},
            {'name': 'develop', 'is_default': False, 'last_commit': 'def456'},
            {'name': 'feature/new-ui', 'is_default': False, 'last_commit': 'ghi789'}
        ]

        return Response({
            'repository_id': repository.id,
            'branches': branches
        })

    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get information about supported repository types."""
        from apps.repositories.models import GitRepository

        type_descriptions = GitRepository.get_repository_types_info()

        serializer = RepositoryTypeDescriptionSerializer(type_descriptions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def cleanup_expired(self, request):
        """Clean up expired repositories."""
        from datetime import timedelta

        expiry_date = timezone.now() - timedelta(days=90)
        expired_count = GitRepository.objects.filter(
            last_commit_date__lt=expiry_date,
            is_active=True
        ).update(is_active=False)

        return Response({
            'message': f'Successfully deactivated {expired_count} expired repositories',
            'count': expired_count
        })

    def destroy(self, request, *args, **kwargs):
        """Soft delete repository by default."""
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
            return Response({'message': f'Repository {instance.id} deactivated successfully'})