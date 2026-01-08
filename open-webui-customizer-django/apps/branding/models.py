"""
Django models for branding functionality.

This module contains models for managing branding templates and assets,
allowing customization of the Open WebUI interface with custom logos,
colors, themes, and other visual elements.
"""

import os
import uuid
from django.db import models
from django.core.files.storage import default_storage
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import BaseDescriptionModel, TimeStampedModel, TimestampedMetadataModel


class BrandingTemplate(BaseDescriptionModel):
    """
    A branding template defines the visual identity customization for Open WebUI.
    
    It contains replacement rules for text/brand elements and can be associated
    with multiple assets like logos, favicons, and theme files.
    
    Inherits from BaseDescriptionModel which provides:
    - name (CharField, unique, indexed)
    - description (TextField, optional)
    - created_at, updated_at timestamps
    - is_active status
    """
    brand_name = models.CharField(
        max_length=255,
        verbose_name="Brand Name",
        help_text="The brand name to display in the UI"
    )
    replacement_rules = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Replacement Rules",
        help_text="JSON object containing text/brand replacement rules"
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name="Is Default",
        help_text="Whether this is the default branding template"
    )
    
    class Meta:
        verbose_name = "Branding Template"
        verbose_name_plural = "Branding Templates"
        ordering = ['-is_default', 'name']
        indexes = [
            models.Index(fields=['brand_name']),
            models.Index(fields=['is_default']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.brand_name})"
    
    def save(self, *args, **kwargs):
        """Ensure only one default template exists."""
        if self.is_default:
            # Set all other templates to non-default
            BrandingTemplate.objects.filter(
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        """Get the absolute URL for this template."""
        return reverse('branding:template_detail', kwargs={'pk': self.pk})
    
    def get_replacement_rule(self, key, default=None):
        """Get a specific replacement rule by key."""
        return self.replacement_rules.get(key, default)
    
    def set_replacement_rule(self, key, value):
        """Set a specific replacement rule."""
        if self.replacement_rules is None:
            self.replacement_rules = {}
        self.replacement_rules[key] = value
        self.save()


def get_asset_upload_path(instance, filename):
    """
    Generate upload path for branding assets.
    
    Assets are stored in organized directories by template and type.
    """
    # Generate safe filename
    safe_filename = slugify(filename.split('.')[0])
    extension = filename.split('.')[-1] if '.' in filename else ''
    unique_filename = f"{safe_filename}_{uuid.uuid4().hex[:8]}.{extension}"
    
    return os.path.join(
        'branding_assets',
        str(instance.template.id),
        instance.file_type,
        unique_filename
    )


class BrandingAsset(TimeStampedModel):
    """
    A branding asset is a file associated with a branding template.
    
    Assets can be logos, favicons, CSS themes, images, or other files
    that customize the visual appearance of the Open WebUI.
    
    Inherits from TimeStampedModel which provides:
    - created_at, updated_at timestamps
    """
    class AssetType(models.TextChoices):
        LOGO = 'logo', 'Logo'
        FAVICON = 'favicon', 'Favicon'
        THEME = 'theme', 'Theme CSS'
        BACKGROUND = 'background', 'Background Image'
        ICON = 'icon', 'Icon'
        FONT = 'font', 'Font File'
        CUSTOM = 'custom', 'Custom'
    
    template = models.ForeignKey(
        BrandingTemplate,
        on_delete=models.CASCADE,
        related_name='assets',
        verbose_name="Template",
        help_text="The branding template this asset belongs to"
    )
    file_name = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="File Name",
        help_text="Original filename of the asset"
    )
    file_type = models.CharField(
        max_length=50,
        choices=AssetType.choices,
        default=AssetType.CUSTOM,
        db_index=True,
        verbose_name="File Type",
        help_text="Type of branding asset"
    )
    file = models.FileField(
        upload_to=get_asset_upload_path,
        max_length=1024,
        verbose_name="File",
        help_text="The asset file"
    )
    file_size = models.PositiveIntegerField(
        editable=False,
        verbose_name="File Size",
        help_text="File size in bytes"
    )
    mime_type = models.CharField(
        max_length=100,
        editable=False,
        verbose_name="MIME Type",
        help_text="MIME type of the file"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Optional description of this asset"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Whether this asset is currently active"
    )
    
    class Meta:
        verbose_name = "Branding Asset"
        verbose_name_plural = "Branding Assets"
        ordering = ['file_type', 'file_name']
        indexes = [
            models.Index(fields=['template', 'file_type']),
            models.Index(fields=['file_type']),
            models.Index(fields=['is_active']),
        ]
        unique_together = [
            ['template', 'file_name', 'file_type']
        ]
    
    def __str__(self):
        return f"{self.template.name} - {self.get_file_type_display()}: {self.file_name}"
    
    def save(self, *args, **kwargs):
        """Auto-populate file metadata before saving."""
        if self.file:
            # Set file size
            self.file_size = self.file.size
            
            # Set MIME type based on file extension
            import mimetypes
            mime_type, _ = mimetypes.guess_type(self.file.name)
            self.mime_type = mime_type or 'application/octet-stream'
        
        # Set file_name from uploaded file if not provided
        if self.file and not self.file_name:
            self.file_name = os.path.basename(self.file.name)
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        """Get the absolute URL for this asset."""
        return reverse('branding:asset_detail', kwargs={'pk': self.pk})
    
    @property
    def file_url(self):
        """Get the public URL of the file."""
        if self.file:
            return self.file.url
        return None
    
    @property
    def file_extension(self):
        """Get the file extension."""
        if self.file:
            return os.path.splitext(self.file.name)[1].lower()
        return None
    
    @property
    def is_image(self):
        """Check if this asset is an image file."""
        if not self.mime_type:
            return False
        return self.mime_type.startswith('image/')
    
    @property
    def is_css(self):
        """Check if this asset is a CSS file."""
        return self.file_extension in ['.css']
    
    @property
    def is_font(self):
        """Check if this asset is a font file."""
        return self.file_extension in ['.ttf', '.otf', '.woff', '.woff2', '.eot']
    
    def duplicate(self, new_template=None):
        """
        Create a duplicate of this asset.
        
        If new_template is provided, the duplicate will be associated
        with that template instead of the original.
        """
        # Copy the file
        if self.file:
            old_file_path = self.file.path
            new_filename = f"copy_{self.file_name}"
            
        asset_copy = BrandingAsset(
            template=new_template or self.template,
            file_name=new_filename,
            file_type=self.file_type,
            description=f"Copy of {self.description}" if self.description else "",
            is_active=self.is_active,
        )
        
        if self.file:
            # Duplicate the actual file
            with open(old_file_path, 'rb') as f:
                asset_copy.file.save(new_filename, f, save=False)
        
        asset_copy.save()
        return asset_copy


class BrandingTemplateManager(models.Manager):
    """Custom manager for BrandingTemplate with common query methods."""
    
    def default(self):
        """Get the default branding template."""
        return self.filter(is_default=True).first()
    
    def active(self):
        """Get all active branding templates."""
        return self.filter(is_active=True)
    
    def with_assets(self, asset_type=None):
        """Get templates with assets, optionally filtered by type."""
        templates = self.prefetch_related('assets')
        if asset_type:
            templates = templates.filter(assets__file_type=asset_type)
        return templates.distinct()


# Add custom manager to BrandingTemplate
BrandingTemplate.add_to_class('objects', BrandingTemplateManager())


# Signal receivers for file cleanup
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver

@receiver(pre_delete, sender=BrandingAsset)
def delete_asset_file(sender, instance, **kwargs):
    """Delete the actual file when a BrandingAsset is deleted."""
    if instance.file:
        if default_storage.exists(instance.file.name):
            default_storage.delete(instance.file.name)


@receiver(post_save, sender=BrandingTemplate)
def template_saved(sender, instance, created, **kwargs):
    """Handle post-save actions for BrandingTemplate."""
    if created and instance.is_default:
        # If this is a new default template, deactivate others
        BrandingTemplate.objects.filter(
            is_default=True
        ).exclude(pk=instance.pk).update(is_default=False)
