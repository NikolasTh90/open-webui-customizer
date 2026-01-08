"""
Tests for branding app models.
"""

import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.branding.models import BrandingTemplate, BrandingAsset
from apps.core.tests.factories import (
    BrandingTemplateFactory,
    BrandingAssetFactory
)


class BrandingTemplateTest(TestCase):
    """Test cases for BrandingTemplate model."""
    
    def setUp(self):
        """Set up test data."""
        self.template = BrandingTemplateFactory()
    
    def test_branding_template_creation(self):
        """Test BrandingTemplate creation."""
        self.assertTrue(isinstance(self.template, BrandingTemplate))
        self.assertEqual(self.template.__str__(), self.template.name)
    
    def test_branding_template_fields(self):
        """Test BrandingTemplate fields."""
        template = BrandingTemplate.objects.create(
            name="Test Template",
            description="Test description",
            primary_color="#ff0000",
            secondary_color="#00ff00",
            accent_color="#0000ff",
            background_color="#ffffff",
            text_color="#000000",
            logo_url="https://example.com/logo.png",
            favicon_url="https://example.com/favicon.ico",
            custom_css="body { margin: 0; }",
            css_variables={"font-size": "16px"},
            is_active=True,
            is_default=True
        )
        
        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.primary_color, "#ff0000")
        self.assertEqual(template.custom_css, "body { margin: 0; }")
        self.assertEqual(template.css_variables, {"font-size": "16px"})
        self.assertTrue(template.is_active)
        self.assertTrue(template.is_default)
    
    def test_unique_default_template(self):
        """Test that only one template can be marked as default."""
        # Create first default template
        template1 = BrandingTemplateFactory(is_default=True)
        
        # Create second template as default
        with self.assertRaises(ValidationError):
            template2 = BrandingTemplateFactory(is_default=True)
            template2.clean()
    
    def test_default_template_ordering(self):
        """Test that default templates come first in ordering."""
        # Create templates
        default_template = BrandingTemplateFactory(is_default=True, name="Default")
        active_template = BrandingTemplateFactory(is_active=True, name="Active")
        inactive_template = BrandingTemplateFactory(is_active=False, name="Inactive")
        
        templates = list(BrandingTemplate.objects.all())
        self.assertEqual(templates[0], default_template)
        self.assertTrue(templates[1].is_active)
        self.assertFalse(templates[2].is_active)
    
    def test_color_validation(self):
        """Test color field validation."""
        # Valid colors
        valid_colors = ["#ff0000", "#00ff00", "#0000ff", "#ffffff", "#000000"]
        for color in valid_colors:
            template = BrandingTemplateFactory(**{color: color})
            self.assertEqual(getattr(template, color), color)
        
        # Invalid colors
        invalid_colors = ["red", "ff0000", "gg0000", "#gg0000", "#fffff"]
        for color in invalid_colors:
            with self.assertRaises(ValidationError):
                BrandingTemplateFactory(**{color: color})
    
    def test_metadata_operations(self):
        """Test metadata field operations."""
        template = BrandingTemplateFactory(metadata={"version": "1.0"})
        
        # Update metadata
        template.metadata["updated"] = True
        template.save()
        
        template.refresh_from_db()
        self.assertTrue(template.metadata["updated"])
    
    def test_queryset_active(self):
        """Test custom queryset for active templates."""
        active_template = BrandingTemplateFactory(is_active=True)
        inactive_template = BrandingTemplateFactory(is_active=False)
        
        active_templates = BrandingTemplate.objects.active()
        self.assertIn(active_template, active_templates)
        self.assertNotIn(inactive_template, active_templates)
    
    def test_queryset_default(self):
        """Test custom queryset for default template."""
        default_template = BrandingTemplateFactory(is_default=True)
        non_default_template = BrandingTemplateFactory(is_default=False)
        
        default_templates = BrandingTemplate.objects.default()
        self.assertEqual(default_templates.count(), 1)
        self.assertEqual(default_templates.first(), default_template)


class BrandingAssetTest(TestCase):
    """Test cases for BrandingAsset model."""
    
    def setUp(self):
        """Set up test data."""
        self.asset = BrandingAssetFactory()
    
    def test_branding_asset_creation(self):
        """Test BrandingAsset creation."""
        self.assertTrue(isinstance(self.asset, BrandingAsset))
        self.assertEqual(self.asset.__str__(), self.asset.file_name)
    
    def test_branding_asset_fields(self):
        """Test BrandingAsset fields."""
        asset = BrandingAsset.objects.create(
            file_name="test.png",
            file_type="logo",
            file_size=100000,
            description="Test asset",
            file_url="https://example.com/test.png",
            template=self.asset.template
        )
        
        self.assertEqual(asset.file_name, "test.png")
        self.assertEqual(asset.file_type, "logo")
        self.assertEqual(asset.description, "Test asset")
    
    def test_file_type_validation(self):
        """Test file_type field validation."""
        valid_types = ["logo", "favicon", "icon", "background", "banner"]
        for file_type in valid_types:
            asset = BrandingAssetFactory(file_type=file_type)
            self.assertEqual(asset.file_type, file_type)
    
    def test_get_human_file_size(self):
        """Test get_human_file_size method."""
        # Test bytes
        asset = BrandingAssetFactory(file_size_bytes=500)
        self.assertEqual(asset.get_human_file_size(), "500.0 B")
        
        # Test KB
        asset.file_size_bytes = 1500
        self.assertEqual(asset.get_human_file_size(), "1.5 KB")
        
        # Test MB
        asset.file_size_bytes = 1500000
        self.assertEqual(asset.get_human_file_size(), "1.5 MB")
        
        # Test GB
        asset.file_size_bytes = 1500000000
        self.assertEqual(asset.get_human_file_size(), "1.5 GB")
    
    def test_is_available_property(self):
        """Test is_available property."""
        # Available asset (not expired)
        asset = BrandingAssetFactory(
            status=1,  # Available
            expires_at=timezone.now() + timezone.timedelta(days=1)
        )
        self.assertTrue(asset.is_available)
        
        # Expired asset
        asset = BrandingAssetFactory(
            status=1,  # Available
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )
        self.assertFalse(asset.is_available)
        
        # Deleted asset
        asset = BrandingAssetFactory(status=3)  # Deleted
        self.assertFalse(asset.is_available)
    
    def test_is_expired_property(self):
        """Test is_expired property."""
        # Not expired
        asset = BrandingAssetFactory(
            expires_at=timezone.now() + timezone.timedelta(days=1)
        )
        self.assertFalse(asset.is_expired)
        
        # Expired
        asset = BrandingAssetFactory(
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )
        self.assertTrue(asset.is_expired)
    
    def test_mark_as_available(self):
        """Test mark_as_available method."""
        asset = BrandingAssetFactory(status=0)  # Pending
        asset.mark_as_available()
        
        asset.refresh_from_db()
        self.assertEqual(asset.status, 1)  # Available
    
    def test_record_download(self):
        """Test record_download method."""
        asset = BrandingAssetFactory(download_count=5)
        asset.record_download()
        
        asset.refresh_from_db()
        self.assertEqual(asset.download_count, 6)
    
    def test_asset_template_relationship(self):
        """Test relationship with BrandingTemplate."""
        template = BrandingTemplateFactory()
        asset = BrandingAssetFactory(template=template)
        
        self.assertEqual(asset.template, template)
        self.assertIn(asset, template.brandingasset_set.all())


class BrandingAssetManagerTest(TestCase):
    """Test cases for BrandingAssetManager."""
    
    def test_available_assets(self):
        """Test getting available assets."""
        available_asset = BrandingAssetFactory(
            status=1,  # Available
            expires_at=timezone.now() + timezone.timedelta(days=1)
        )
        expired_asset = BrandingAssetFactory(
            status=1,  # Available
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )
        deleted_asset = BrandingAssetFactory(status=3)  # Deleted
        
        available_assets = BrandingAsset.objects.available()
        self.assertIn(available_asset, available_assets)
        self.assertNotIn(expired_asset, available_assets)
        self.assertNotIn(deleted_asset, available_assets)
    
    def test_expired_assets(self):
        """Test getting expired assets."""
        expired_asset = BrandingAssetFactory(
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )
        valid_asset = BrandingAssetFactory(
            expires_at=timezone.now() + timezone.timedelta(days=1)
        )
        
        expired_assets = BrandingAsset.objects.expired()
        self.assertIn(expired_asset, expired_assets)
        self.assertNotIn(valid_asset, expired_assets)
    
    def test_cleanup_expired_outputs(self):
        """Test cleanup of expired assets."""
        expired_asset1 = BrandingAssetFactory(
            status=1,  # Available
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )
        expired_asset2 = BrandingAssetFactory(
            status=1,  # Available
            expires_at=timezone.now() - timezone.timedelta(days=2)
        )
        valid_asset = BrandingAssetFactory(
            status=1,  # Available
            expires_at=timezone.now() + timezone.timedelta(days=1)
        )
        
        cleaned, failed = BrandingAsset.cleanup_expired_assets()
        self.assertEqual(cleaned, 2)
        self.assertEqual(failed, 0)
        
        # Check that expired assets are marked as expired
        expired_asset1.refresh_from_db()
        expired_asset2.refresh_from_db()
        self.assertTrue(expired_asset1.is_expired)
        self.assertTrue(expired_asset2.is_expired)
        
        # Valid asset should remain available
        valid_asset.refresh_from_db()
        self.assertTrue(valid_asset.is_available)