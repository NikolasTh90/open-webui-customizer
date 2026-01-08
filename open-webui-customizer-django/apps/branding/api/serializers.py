"""
Django REST Framework serializers for branding app.

This module provides serializers for converting BrandingTemplate and BrandingAsset models
and related data to/from JSON representations for the API.
"""

from rest_framework import serializers
from apps.branding.models import BrandingTemplate, BrandingAsset


class BrandingAssetSerializer(serializers.ModelSerializer):
    """
    Serializer for BrandingAsset model.

    Handles serialization of branding assets with file information and URLs.
    """

    file_type_display = serializers.CharField(
        source='get_file_type_display',
        read_only=True
    )

    file_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()

    class Meta:
        model = BrandingAsset
        fields = [
            'id', 'file_name', 'file_type', 'file_type_display',
            'file_size', 'description', 'file_url', 'preview_url',
            'template', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_file_url(self, obj):
        """Get the file URL for the asset."""
        return obj.file_url or f"/media/branding/{obj.file_name}"

    def get_preview_url(self, obj):
        """Get preview URL for the asset."""
        if obj.file_type in ['logo', 'favicon', 'icon']:
            return self.get_file_url(obj)
        return None


class BrandingTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for BrandingTemplate model.

    Handles serialization of branding templates with assets and configuration.
    """

    assets = BrandingAssetSerializer(many=True, read_only=True, source='assets')
    assets_count = serializers.SerializerMethodField()
    is_default_display = serializers.CharField(
        source='get_is_default_display',
        read_only=True
    )

    class Meta:
        model = BrandingTemplate
        fields = [
            'id', 'name', 'description', 'is_active', 'is_default',
            'is_default_display', 'primary_color', 'secondary_color',
            'accent_color', 'background_color', 'text_color',
            'custom_css', 'css_variables', 'assets', 'assets_count',
            'created_at', 'updated_at', 'metadata'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_assets_count(self, obj):
        """Get count of associated assets."""
        return obj.assets.count()


class BrandingTemplateCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new branding templates.

    Includes validation for color formats and CSS.
    """

    class Meta:
        model = BrandingTemplate
        fields = [
            'name', 'description', 'is_default', 'primary_color',
            'secondary_color', 'accent_color', 'background_color',
            'text_color', 'custom_css', 'css_variables', 'metadata'
        ]

    def validate_name(self, value):
        """Validate template name uniqueness."""
        queryset = BrandingTemplate.objects.filter(name=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("A branding template with this name already exists")

        return value

    def validate_primary_color(self, value):
        """Validate color format."""
        return self._validate_color(value, 'primary_color')

    def validate_secondary_color(self, value):
        """Validate color format."""
        return self._validate_color(value, 'secondary_color')

    def validate_accent_color(self, value):
        """Validate color format."""
        return self._validate_color(value, 'accent_color')

    def validate_background_color(self, value):
        """Validate color format."""
        return self._validate_color(value, 'background_color')

    def validate_text_color(self, value):
        """Validate color format."""
        return self._validate_color(value, 'text_color')

    def _validate_color(self, value, field_name):
        """Validate color format (hex, rgb, rgba, hsl, hsla, or named colors)."""
        if not value:
            return value

        import re

        # Hex colors
        if re.match(r'^#[0-9a-fA-F]{3,8}$', value):
            return value

        # RGB/RGBA
        if re.match(r'^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[0-9.]+\s*)?\)$', value):
            return value

        # HSL/HSLA
        if re.match(r'^hsla?\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*(?:,\s*[0-9.]+\s*)?\)$', value):
            return value

        # Named colors (basic validation - just check it's not empty and contains valid chars)
        if re.match(r'^[a-zA-Z\s-]+$', value.strip()):
            return value

        raise serializers.ValidationError(f"Invalid color format for {field_name}")

    def validate_custom_css(self, value):
        """Validate custom CSS (basic validation)."""
        if not value:
            return value

        # Basic CSS validation - check for balanced braces and semicolons
        if value.count('{') != value.count('}'):
            raise serializers.ValidationError("Unbalanced braces in custom CSS")

        return value

    def validate_css_variables(self, value):
        """Validate CSS variables structure."""
        if not value:
            return value

        if not isinstance(value, dict):
            raise serializers.ValidationError("CSS variables must be a dictionary")

        # Validate variable names and values
        for key, val in value.items():
            if not key.startswith('--'):
                raise serializers.ValidationError(f"CSS variable '{key}' must start with '--'")
            if not isinstance(val, str):
                raise serializers.ValidationError(f"CSS variable '{key}' value must be a string")

        return value


class BrandingTemplateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing branding templates.

    Only allows updating certain fields after creation.
    """

    class Meta:
        model = BrandingTemplate
        fields = [
            'name', 'description', 'is_active', 'is_default',
            'primary_color', 'secondary_color', 'accent_color',
            'background_color', 'text_color', 'custom_css',
            'css_variables', 'metadata'
        ]
        read_only_fields = ['name']  # Name cannot be changed


class BrandingAssetCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new branding assets.

    Handles file upload validation and processing.
    """

    class Meta:
        model = BrandingAsset
        fields = [
            'file_name', 'file_type', 'description', 'template'
        ]

    def validate_file_name(self, value):
        """Validate file name and extension."""
        if not value:
            raise serializers.ValidationError("File name is required")

        # Check for valid file extensions based on file type
        file_type = self.initial_data.get('file_type')
        if file_type:
            valid_extensions = {
                'logo': ['.png', '.jpg', '.jpeg', '.svg', '.webp'],
                'favicon': ['.ico', '.png', '.svg'],
                'icon': ['.png', '.jpg', '.jpeg', '.svg', '.webp'],
                'background': ['.png', '.jpg', '.jpeg', '.svg', '.webp'],
                'font': ['.ttf', '.woff', '.woff2'],
                'css': ['.css'],
                'other': []  # Allow any extension for other types
            }

            extensions = valid_extensions.get(file_type, [])
            if extensions:
                file_ext = value.lower().split('.')[-1]
                if f'.{file_ext}' not in extensions:
                    raise serializers.ValidationError(
                        f"Invalid file extension for {file_type}. Allowed: {', '.join(extensions)}"
                    )

        return value

    def validate_file_type(self, value):
        """Validate file type."""
        valid_types = ['logo', 'favicon', 'icon', 'background', 'font', 'css', 'other']
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid file type. Must be one of: {', '.join(valid_types)}"
            )
        return value


class BrandingPreviewSerializer(serializers.Serializer):
    """
    Serializer for branding template preview data.
    """

    template_id = serializers.IntegerField(read_only=True)
    preview_html = serializers.CharField(read_only=True)
    css_styles = serializers.CharField(read_only=True)
    assets = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )