"""
Django REST Framework views for branding app.

This module provides API views for branding template and asset management
including CRUD operations, preview generation, and asset handling.
"""

from django.shortcuts import get_object_or_404
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from apps.branding.models import BrandingTemplate, BrandingAsset
from apps.branding.api.serializers import (
    BrandingTemplateSerializer, BrandingTemplateCreateSerializer,
    BrandingTemplateUpdateSerializer, BrandingAssetSerializer,
    BrandingAssetCreateSerializer, BrandingPreviewSerializer
)


class BrandingPagination(PageNumberPagination):
    """Custom pagination for branding resources."""

    page_size = 50
    page_size_query_param = 'per_page'
    max_page_size = 100


class BrandingTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for branding template management.

    Provides CRUD operations for branding templates with preview
    and asset management capabilities.
    """

    queryset = BrandingTemplate.objects.filter(is_active=True).order_by('-created_at')
    pagination_class = BrandingPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return BrandingTemplateCreateSerializer
        elif self.action == 'update':
            return BrandingTemplateUpdateSerializer
        elif self.action == 'partial_update':
            return BrandingTemplateUpdateSerializer
        return BrandingTemplateSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()

        # Filter by default status
        is_default = self.request.query_params.get('is_default')
        if is_default is not None:
            queryset = queryset.filter(is_default=is_default.lower() == 'true')

        # Search by name or description
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(description__icontains=search)
            )

        return queryset

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set this template as the default."""
        template = self.get_object()

        # Unset current default
        BrandingTemplate.objects.filter(is_default=True).update(is_default=False)

        # Set new default
        template.is_default = True
        template.save()

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Generate a preview of the branding template."""
        template = self.get_object()

        # Generate CSS from template
        css_styles = self._generate_css(template)

        # Generate HTML preview
        preview_html = self._generate_preview_html(template)

        # Get assets info
        assets = []
        for asset in template.brandingasset_set.all():
            assets.append({
                'id': asset.id,
                'file_name': asset.file_name,
                'file_type': asset.file_type,
                'url': asset.file_url or f"/media/branding/{asset.file_name}"
            })

        preview_data = {
            'template_id': template.id,
            'preview_html': preview_html,
            'css_styles': css_styles,
            'assets': assets
        }

        serializer = BrandingPreviewSerializer(preview_data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a duplicate of this template."""
        template = self.get_object()

        # Create new template with copied data
        new_template_data = {
            'name': f"{template.name} (Copy)",
            'description': template.description,
            'primary_color': template.primary_color,
            'secondary_color': template.secondary_color,
            'accent_color': template.accent_color,
            'background_color': template.background_color,
            'text_color': template.text_color,
            'custom_css': template.custom_css,
            'css_variables': template.css_variables.copy() if template.css_variables else {},
            'metadata': template.metadata.copy() if template.metadata else {}
        }

        serializer = BrandingTemplateCreateSerializer(data=new_template_data)
        if serializer.is_valid():
            new_template = serializer.save()

            # Copy assets (this would need file copying logic in production)
            for asset in template.brandingasset_set.all():
                BrandingAsset.objects.create(
                    file_name=f"{asset.file_name.rsplit('.', 1)[0]}_copy.{asset.file_name.rsplit('.', 1)[1]}",
                    file_type=asset.file_type,
                    file_size=asset.file_size,
                    description=asset.description,
                    template=new_template,
                    metadata=asset.metadata.copy() if asset.metadata else {}
                )

            response_serializer = BrandingTemplateSerializer(new_template)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def defaults(self, request):
        """Get default branding templates."""
        defaults = self.get_queryset().filter(is_default=True)

        # If no default is set, return the first active template
        if not defaults.exists():
            defaults = self.get_queryset()[:1]

        serializer = self.get_serializer(defaults, many=True)
        return Response(serializer.data)

    def _generate_css(self, template):
        """Generate CSS from template configuration."""
        css = f"""
        :root {{
            --primary-color: {template.primary_color or '#007bff'};
            --secondary-color: {template.secondary_color or '#6c757d'};
            --accent-color: {template.accent_color or '#28a745'};
            --background-color: {template.background_color or '#ffffff'};
            --text-color: {template.text_color or '#000000'};
        }}

        body {{
            background-color: var(--background-color);
            color: var(--text-color);
        }}

        .primary {{
            color: var(--primary-color);
        }}

        .secondary {{
            color: var(--secondary-color);
        }}

        .accent {{
            color: var(--accent-color);
        }}
        """

        # Add CSS variables
        if template.css_variables:
            css += "\n        :root {\n"
            for key, value in template.css_variables.items():
                css += f"            {key}: {value};\n"
            css += "        }\n"

        # Add custom CSS
        if template.custom_css:
            css += f"\n        {template.custom_css}\n"

        return css

    def _generate_preview_html(self, template):
        """Generate HTML preview for the template."""
        return f"""
        <div class="branding-preview">
            <header style="background-color: {template.primary_color or '#007bff'}; color: white; padding: 1rem;">
                <h1>{template.name}</h1>
                <p>{template.description or 'Branding template preview'}</p>
            </header>

            <main style="padding: 2rem;">
                <div class="color-palette">
                    <div class="color-sample" style="background-color: {template.primary_color or '#007bff'};">
                        Primary: {template.primary_color or '#007bff'}
                    </div>
                    <div class="color-sample" style="background-color: {template.secondary_color or '#6c757d'};">
                        Secondary: {template.secondary_color or '#6c757d'}
                    </div>
                    <div class="color-sample" style="background-color: {template.accent_color or '#28a745'};">
                        Accent: {template.accent_color or '#28a745'}
                    </div>
                </div>

                <div class="content-sample" style="margin-top: 2rem;">
                    <h2 class="primary">Sample Content</h2>
                    <p>This is how your content will look with this branding template.</p>
                    <button class="accent" style="background-color: {template.accent_color or '#28a745'}; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px;">
                        Sample Button
                    </button>
                </div>
            </main>
        </div>
        """


class BrandingAssetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for branding asset management.

    Provides CRUD operations for branding assets with file handling.
    """

    queryset = BrandingAsset.objects.all().order_by('-created_at')
    pagination_class = BrandingPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return BrandingAssetCreateSerializer
        return BrandingAssetSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()

        # Filter by template
        template = self.request.query_params.get('template')
        if template:
            queryset = queryset.filter(template_id=template)

        # Filter by file type
        file_type = self.request.query_params.get('file_type')
        if file_type:
            queryset = queryset.filter(file_type=file_type)

        # Search by file name or description
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(file_name__icontains=search) |
                models.Q(description__icontains=search)
            )

        return queryset

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the asset file."""
        asset = self.get_object()

        # This would serve the file or redirect to download URL
        return Response({
            'download_url': asset.file_url or f"/media/branding/{asset.file_name}",
            'filename': asset.file_name,
            'file_size': asset.file_size,
            'file_type': asset.file_type
        })

    def destroy(self, request, *args, **kwargs):
        """Delete asset and clean up files."""
        instance = self.get_object()

        # TODO: Add file cleanup logic here
        # This would delete the actual file from storage

        self.perform_destroy(instance)
        return Response({'message': f'Asset {instance.file_name} deleted successfully'})