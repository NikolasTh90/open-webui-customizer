"""
Django admin configuration for branding models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

try:
    from unfold.admin import ModelAdmin, TabularInline
    from unfold.decorators import display
except ImportError:
    # Fallback to standard Django admin if unfold is not available
    ModelAdmin = admin.ModelAdmin
    TabularInline = admin.TabularInline
    def display(description=None):
        def decorator(func):
            if description:
                func.short_description = description
            return func
        return decorator

from .models import BrandingTemplate, BrandingAsset


@admin.register(BrandingTemplate)
class BrandingTemplateAdmin(ModelAdmin):
    """Admin configuration for BrandingTemplate model."""
    
    list_display = [
        'name',
        'is_active',
        'is_default',
        'preview_colors',
        'created_at',
        'updated_at'
    ]
    list_filter = [
        'is_active',
        'is_default',
        'created_at',
        'updated_at'
    ]
    search_fields = [
        'name',
        'description'
    ]
    readonly_fields = [
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'description',
                'is_active',
                'is_default'
            )
        }),
        ('Visual Settings', {
            'fields': (
                'primary_color',
                'secondary_color',
                'accent_color',
                'background_color',
                'text_color',
                'logo_url',
                'favicon_url'
            )
        }),
        ('CSS Configuration', {
            'fields': (
                'custom_css',
                'css_variables'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'metadata',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    @display(description="Colors")
    def preview_colors(self, obj):
        """Display color preview swatches."""
        colors = []
        
        if obj.primary_color:
            colors.append(
                f'<span style="background-color: {obj.primary_color}; '
                f'width: 20px; height: 20px; display: inline-block; '
                f'border: 1px solid #ccc; margin-right: 2px;" '
                f'title="Primary: {obj.primary_color}"></span>'
            )
        
        if obj.secondary_color:
            colors.append(
                f'<span style="background-color: {obj.secondary_color}; '
                f'width: 20px; height: 20px; display: inline-block; '
                f'border: 1px solid #ccc; margin-right: 2px;" '
                f'title="Secondary: {obj.secondary_color}"></span>'
            )
        
        if obj.accent_color:
            colors.append(
                f'<span style="background-color: {obj.accent_color}; '
                f'width: 20px; height: 20px; display: inline-block; '
                f'border: 1px solid #ccc; margin-right: 2px;" '
                f'title="Accent: {obj.accent_color}"></span>'
            )
        
        return mark_safe(''.join(colors)) if colors else 'No colors'
    
    actions = ['make_active', 'make_inactive', 'set_as_default']
    
    def make_active(self, request, queryset):
        """Mark selected templates as active."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} templates marked as active.'
        )
    make_active.short_description = 'Mark selected templates as active'
    
    def make_inactive(self, request, queryset):
        """Mark selected templates as inactive."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} templates marked as inactive.'
        )
    make_inactive.short_description = 'Mark selected templates as inactive'
    
    def set_as_default(self, request, queryset):
        """Set selected template as default (only one allowed)."""
        if queryset.count() > 1:
            self.message_user(
                request,
                'Cannot set multiple templates as default. Please select only one.',
                level='error'
            )
            return
        
        # Clear all existing defaults
        BrandingTemplate.objects.all().update(is_default=False)
        
        # Set new default
        queryset.update(is_default=True)
        self.message_user(
            request,
            'Template set as default.'
        )
    set_as_default.short_description = 'Set selected template as default'


class BrandingAssetInline(TabularInline):
    """Inline admin for BrandingAsset model."""
    model = BrandingAsset
    extra = 1
    fields = [
        'asset_type',
        'asset_file',
        'asset_url',
        'description'
    ]
    readonly_fields = []


@admin.register(BrandingAsset)
class BrandingAssetAdmin(ModelAdmin):
    """Admin configuration for BrandingAsset model."""
    
    list_display = [
        'file_name',
        'file_type',
        'template',
        'asset_preview',
        'file_size',
        'created_at'
    ]
    list_filter = [
        'file_type',
        'template',
        'created_at'
    ]
    search_fields = [
        'file_name',
        'description',
        'template__name'
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'file_size'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'file_name',
                'template',
                'file_type',
                'description'
            )
        }),
        ('Asset Files', {
            'fields': (
                'file',
                'file_url',
                'file_size'
            )
        }),
        ('Metadata', {
            'fields': (
                'metadata',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    @display(description="Preview")
    def asset_preview(self, obj):
        """Display a preview of the asset."""
        if obj.file:
            if obj.file_type in ['logo', 'favicon', 'icon']:
                return mark_safe(
                    f'<img src="{obj.file.url}" '
                    f'style="max-height: 50px; max-width: 50px;" '
                    f'alt="{obj.file_name}" />'
                )
            else:
                return format_html(
                    '<a href="{0}" download>{1}</a>',
                    obj.file.url,
                    obj.file.name.split('/')[-1]
                )
        return 'No asset'
    
    @display(description="Size")
    def file_size(self, obj):
        """Display the file size."""
        # Use the file_size field from the model
        if obj.file_size:
            size = obj.file_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        return 'N/A'
