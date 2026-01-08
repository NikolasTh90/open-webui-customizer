"""
Tests for core app models.
"""

import pytest
from django.test import TestCase
from django.utils import timezone
from apps.core.models import (
    TimeStampedModel, SoftDeleteModel, UUIDModel, ActiveModel, MetadataModel,
    ExpirableModel, AuditModel, BaseNameModel, BaseDescriptionModel,
    TimestampedMetadataModel, TimestampedExpirableModel
)


class BaseModelTest(TestCase):
    """Test cases for BaseModel."""
    
    def test_model_string_representation(self):
        """Test that BaseModel string representation works."""
        # This is an abstract model, so we'll test through a concrete implementation
        from apps.branding.models import BrandingTemplate
        
        template = BrandingTemplate(name="Test Template")
        self.assertEqual(str(template), "Test Template")
    
    def test_base_model_fields(self):
        """Test that BaseModel provides expected fields."""
        from apps.branding.models import BrandingTemplate
        
        template = BrandingTemplate.objects.create(
            name="Test Template",
            description="Test description"
        )
        
        # Check that the model has the expected fields
        self.assertTrue(hasattr(template, 'id'))
        self.assertTrue(hasattr(template, 'metadata'))
        self.assertIsNotNone(template.id)


class TimestampedModelTest(TestCase):
    """Test cases for TimestampedModel."""
    
    def test_created_at_auto_now_add(self):
        """Test that created_at is set on creation."""
        from apps.branding.models import BrandingTemplate
        
        template = BrandingTemplate.objects.create(
            name="Test Template",
            description="Test description"
        )
        
        self.assertIsNotNone(template.created_at)
        self.assertTrue(
            timezone.is_aware(template.created_at),
            "created_at should be timezone-aware"
        )
    
    def test_updated_at_auto_now(self):
        """Test that updated_at is updated on save."""
        from apps.branding.models import BrandingTemplate
        
        template = BrandingTemplate.objects.create(
            name="Test Template",
            description="Test description"
        )
        
        original_updated_at = template.updated_at
        
        # Wait a bit to ensure timestamp difference
        import time
        time.sleep(0.1)
        
        template.description = "Updated description"
        template.save()
        
        template.refresh_from_db()
        
        self.assertGreater(template.updated_at, original_updated_at)


class MetadataModelTest(TestCase):
    """Test cases for MetadataModel."""

    def test_metadata_field_default(self):
        """Test that metadata field defaults to empty dict."""
        from apps.pipelines.models import PipelineRun

        pipeline_run = PipelineRun.objects.create(
            name="Test Pipeline Run",
            status="running"
        )

        self.assertEqual(pipeline_run.metadata, {})

    def test_metadata_field_storage(self):
        """Test that metadata field stores JSON data correctly."""
        from apps.pipelines.models import PipelineRun

        test_metadata = {
            "version": "1.0",
            "author": "Test Author",
            "tags": ["test", "pipeline"]
        }

        pipeline_run = PipelineRun.objects.create(
            name="Test Pipeline Run",
            status="running",
            metadata=test_metadata
        )

        pipeline_run.refresh_from_db()
        self.assertEqual(pipeline_run.metadata, test_metadata)

    def test_metadata_field_update(self):
        """Test that metadata field can be updated."""
        from apps.pipelines.models import PipelineRun

        pipeline_run = PipelineRun.objects.create(
            name="Test Pipeline Run",
            status="running"
        )

        # Update metadata
        pipeline_run.metadata = {"updated": True}
        pipeline_run.save()

        pipeline_run.refresh_from_db()
        self.assertEqual(pipeline_run.metadata, {"updated": True})