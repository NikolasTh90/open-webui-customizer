"""
Django REST Framework serializers for repositories app.

This module provides serializers for converting GitRepository models
and related data to/from JSON representations for the API.
"""

from rest_framework import serializers
from apps.repositories.models import GitRepository, RepositoryType, VerificationStatus


class GitRepositorySerializer(serializers.ModelSerializer):
    """
    Serializer for GitRepository model.

    Handles serialization/deserialization of Git repository data,
    including verification status and metadata.
    """

    repository_type_display = serializers.CharField(
        source='get_repository_type_display',
        read_only=True
    )

    verification_status_display = serializers.CharField(
        source='get_verification_status_display',
        read_only=True
    )

    is_expired = serializers.SerializerMethodField()
    days_since_last_commit = serializers.SerializerMethodField()

    class Meta:
        model = GitRepository
        fields = [
            'id', 'name', 'repository_url', 'repository_type',
            'repository_type_display', 'default_branch', 'is_active',
            'is_verified', 'verification_status', 'verification_status_display',
            'is_experimental', 'branch', 'commit_hash', 'last_commit_date',
            'is_expired', 'days_since_last_commit', 'created_at', 'updated_at',
            'metadata'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_commit_date']

    def get_is_expired(self, obj):
        """Check if repository data is considered expired."""
        if not obj.last_commit_date:
            return True

        from django.utils import timezone
        from datetime import timedelta

        # Consider expired if no commits in 90 days
        expiry_date = timezone.now() - timedelta(days=90)
        return obj.last_commit_date < expiry_date

    def get_days_since_last_commit(self, obj):
        """Calculate days since last commit."""
        if not obj.last_commit_date:
            return None

        from django.utils import timezone
        delta = timezone.now() - obj.last_commit_date
        return delta.days


class GitRepositoryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new Git repositories.

    Includes validation for repository URLs and types.
    """

    class Meta:
        model = GitRepository
        fields = [
            'name', 'repository_url', 'repository_type', 'default_branch',
            'is_experimental', 'metadata'
        ]

    def validate_repository_url(self, value):
        """Validate repository URL format."""
        import re
        from urllib.parse import urlparse

        # Basic URL validation
        try:
            parsed = urlparse(value)
            if not parsed.scheme or not parsed.netloc:
                raise serializers.ValidationError("Invalid URL format")
        except Exception:
            raise serializers.ValidationError("Invalid URL format")

        # Check for supported Git hosting services
        supported_domains = [
            'github.com', 'gitlab.com', 'bitbucket.org',
            'git.example.com', 'code.example.com'
        ]

        domain = parsed.netloc.lower()
        if not any(domain.endswith(supported) for supported in supported_domains):
            # Allow custom domains but warn
            pass

        return value

    def validate(self, data):
        """Cross-field validation."""
        repository_type = data.get('repository_type')
        repository_url = data.get('repository_url')

        if repository_type and repository_url:
            # Type-specific URL validation
            url_lower = repository_url.lower()

            if repository_type == RepositoryType.GITHUB and 'github.com' not in url_lower:
                raise serializers.ValidationError({
                    'repository_url': 'GitHub repositories must use github.com domain'
                })
            elif repository_type == RepositoryType.GITLAB and 'gitlab.com' not in url_lower:
                raise serializers.ValidationError({
                    'repository_url': 'GitLab repositories must use gitlab.com domain'
                })
            elif repository_type == RepositoryType.BITBUCKET and 'bitbucket.org' not in url_lower:
                raise serializers.ValidationError({
                    'repository_url': 'Bitbucket repositories must use bitbucket.org domain'
                })

        return data


class GitRepositoryUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing Git repositories.

    Only allows updating certain fields after creation.
    """

    class Meta:
        model = GitRepository
        fields = [
            'name', 'default_branch', 'is_active', 'is_experimental',
            'branch', 'metadata'
        ]
        read_only_fields = ['name']  # Name cannot be changed


class GitRepositoryVerificationSerializer(serializers.Serializer):
    """
    Serializer for repository verification results.
    """

    repository_id = serializers.IntegerField(read_only=True)
    verified = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    last_commit_hash = serializers.CharField(read_only=True, allow_null=True)
    last_commit_date = serializers.DateTimeField(read_only=True, allow_null=True)


class RepositoryTypeDescriptionSerializer(serializers.Serializer):
    """
    Serializer for repository type descriptions.
    """

    type = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    supported_domains = serializers.ListField(child=serializers.CharField())
    features = serializers.ListField(child=serializers.CharField())