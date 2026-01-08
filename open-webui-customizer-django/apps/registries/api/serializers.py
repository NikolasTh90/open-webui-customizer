"""
Django REST Framework serializers for registries app.

This module provides serializers for converting ContainerRegistry models
and related data to/from JSON representations for the API.
"""

from rest_framework import serializers
from apps.registries.models import ContainerRegistry, RegistryType


class ContainerRegistrySerializer(serializers.ModelSerializer):
    """
    Serializer for ContainerRegistry model.

    Handles serialization/deserialization of container registry data,
    including connection status and metadata.
    """

    registry_type_display = serializers.CharField(
        source='get_registry_type_display',
        read_only=True
    )

    full_registry_url = serializers.SerializerMethodField()
    is_connected = serializers.SerializerMethodField()

    class Meta:
        model = ContainerRegistry
        fields = [
            'id', 'name', 'registry_url', 'registry_type',
            'registry_type_display', 'is_active', 'namespace',
            'region', 'full_registry_url', 'is_connected',
            'created_at', 'updated_at', 'metadata'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_full_registry_url(self, obj):
        """Get the full registry URL including namespace if applicable."""
        if obj.namespace:
            return f"{obj.registry_url}/{obj.namespace}"
        return obj.registry_url

    def get_is_connected(self, obj):
        """Check if registry connection is verified."""
        # This would implement actual connection checking
        # For now, return a cached status
        return getattr(obj, '_connection_verified', False)


class ContainerRegistryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new container registries.

    Includes validation for registry URLs and authentication.
    """

    class Meta:
        model = ContainerRegistry
        fields = [
            'name', 'registry_url', 'registry_type', 'namespace',
            'region', 'metadata'
        ]

    def validate_registry_url(self, value):
        """Validate registry URL format."""
        from urllib.parse import urlparse

        # Basic URL validation
        try:
            parsed = urlparse(value)
            if not parsed.scheme or not parsed.netloc:
                raise serializers.ValidationError("Invalid URL format")
        except Exception:
            raise serializers.ValidationError("Invalid URL format")

        # Ensure HTTPS for production registries
        if parsed.scheme != 'https':
            raise serializers.ValidationError("Registry URL must use HTTPS")

        return value

    def validate(self, data):
        """Cross-field validation."""
        registry_type = data.get('registry_type')
        registry_url = data.get('registry_url')

        if registry_type and registry_url:
            # Type-specific URL validation
            url_lower = registry_url.lower()

            if registry_type == RegistryType.DOCKER_HUB and 'docker.io' not in url_lower:
                # Docker Hub can use docker.io or index.docker.io
                pass
            elif registry_type == RegistryType.GITHUB_PACKAGES and 'ghcr.io' not in url_lower:
                raise serializers.ValidationError({
                    'registry_url': 'GitHub Container Registry must use ghcr.io domain'
                })
            elif registry_type == RegistryType.GITLAB_REGISTRY and 'registry.gitlab.com' not in url_lower:
                raise serializers.ValidationError({
                    'registry_url': 'GitLab Container Registry must use registry.gitlab.com domain'
                })
            elif registry_type == RegistryType.AWS_ECR and not any(domain in url_lower for domain in ['amazonaws.com', 'amazon.com']):
                raise serializers.ValidationError({
                    'registry_url': 'AWS ECR must use amazonaws.com domain'
                })

        return data


class ContainerRegistryUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing container registries.

    Only allows updating certain fields after creation.
    """

    class Meta:
        model = ContainerRegistry
        fields = [
            'name', 'is_active', 'namespace', 'region', 'metadata'
        ]
        read_only_fields = ['name']  # Name cannot be changed


class ContainerRegistryConnectionSerializer(serializers.Serializer):
    """
    Serializer for registry connection test results.
    """

    registry_id = serializers.IntegerField(read_only=True)
    connected = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    response_time_ms = serializers.IntegerField(read_only=True, allow_null=True)


class RegistryTypeDescriptionSerializer(serializers.Serializer):
    """
    Serializer for registry type descriptions.
    """

    type = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    default_domain = serializers.CharField()
    features = serializers.ListField(child=serializers.CharField())
    requires_credentials = serializers.BooleanField()