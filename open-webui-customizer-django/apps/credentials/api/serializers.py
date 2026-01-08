"""
Django REST Framework serializers for credentials app.

This module provides serializers for converting between Django models
and JSON representations for the API.
"""

from rest_framework import serializers
from apps.credentials.models import Credential, CredentialType


class CredentialSerializer(serializers.ModelSerializer):
    """
    Serializer for Credential model.

    Handles serialization/deserialization of credential data,
    excluding sensitive encrypted information.
    """

    credential_type_display = serializers.CharField(
        source='get_credential_type_display',
        read_only=True
    )

    days_until_expiry = serializers.SerializerMethodField()
    has_expired = serializers.SerializerMethodField()

    class Meta:
        model = Credential
        fields = [
            'id', 'name', 'credential_type',
            'credential_type_display', 'metadata', 'is_active',
            'created_at', 'updated_at', 'expires_at', 'last_used_at',
            'days_until_expiry', 'has_expired'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_used_at']

    def get_days_until_expiry(self, obj):
        """Calculate days until credential expires."""
        if not obj.expires_at:
            return None

        from django.utils import timezone
        now = timezone.now()

        if obj.expires_at < now:
            return 0

        return (obj.expires_at - now).days

    def get_has_expired(self, obj):
        """Check if credential has expired."""
        return obj.is_expired if hasattr(obj, 'is_expired') else False


class CredentialCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new credentials.

    Includes validation for credential data and handles encryption.
    """

    credential_data = serializers.JSONField(
        write_only=True,
        help_text="The credential data to encrypt (structure depends on credential_type)"
    )

    class Meta:
        model = Credential
        fields = [
            'name', 'credential_type', 'credential_data',
            'expires_at', 'metadata'
        ]

    def validate_credential_data(self, value):
        """Validate credential data structure based on type."""
        credential_type = self.initial_data.get('credential_type')

        if not credential_type:
            raise serializers.ValidationError("credential_type is required")

        # Import here to avoid circular imports
        from apps.credentials.models import Credential

        # Create a temporary credential instance to validate
        temp_credential = Credential(credential_type=credential_type)

        try:
            temp_credential._validate_credential_data(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))

        return value

    def create(self, validated_data):
        """Create credential with encrypted data."""
        credential_data = validated_data.pop('credential_data')
        credential = super().create(validated_data)

        # Set and encrypt the credential data
        credential.set_credential_data(credential_data)
        credential.save()

        return credential


class CredentialUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing credentials.

    Only allows updating non-sensitive metadata fields.
    """

    class Meta:
        model = Credential
        fields = ['name', 'is_active', 'expires_at', 'metadata']
        read_only_fields = ['name']  # Name cannot be changed


class CredentialDataUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating credential data.

    Requires the full credential data to be provided for re-encryption.
    """

    credential_data = serializers.JSONField(
        help_text="The new credential data to encrypt"
    )

    def validate_credential_data(self, value):
        """Validate the new credential data."""
        instance = self.context.get('instance')
        if not instance:
            raise serializers.ValidationError("Credential instance required")

        try:
            instance._validate_credential_data(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))

        return value


class CredentialVerificationSerializer(serializers.Serializer):
    """
    Serializer for credential verification results.
    """

    credential_id = serializers.IntegerField(read_only=True)
    valid = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)


class CredentialTypeDescriptionSerializer(serializers.Serializer):
    """
    Serializer for credential type descriptions.
    """

    type = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    required_fields = serializers.ListField(child=serializers.CharField())
    example_data = serializers.JSONField()


class CredentialListSerializer(serializers.Serializer):
    """
    Serializer for paginated credential lists.
    """

    items = CredentialSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    per_page = serializers.IntegerField()
    has_next = serializers.BooleanField()
    has_prev = serializers.BooleanField()