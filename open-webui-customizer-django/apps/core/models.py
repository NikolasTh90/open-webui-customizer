"""
Abstract base models for the Open WebUI Customizer Django project.

This module provides common functionality that will be inherited by all models
across different Django apps, ensuring consistency and reducing code duplication.
"""

from django.db import models
from django.utils import timezone
import uuid


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides created_at and updated_at timestamps.
    
    This model automatically manages timestamp fields for all inheriting models.
    It uses timezone-aware datetime objects and ensures the updated_at field
    is always updated when the model is saved.
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        help_text="Timestamp when the object was first created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Last Updated",
        help_text="Timestamp when the object was last modified"
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]

    def save(self, *args, **kwargs):
        """Ensure updated_at is always updated when saving."""
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class SoftDeleteModel(TimeStampedModel):
    """
    Abstract base model that provides soft-delete functionality.
    
    Instead of actually deleting records, this model marks them as deleted
    using an is_deleted field and a deleted_at timestamp. This allows
    for data recovery and audit trails.
    """
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Is Deleted",
        help_text="Indicates whether this object has been soft-deleted"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Deleted At",
        help_text="Timestamp when the object was soft-deleted"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['is_deleted']),
            models.Index(fields=['deleted_at']),
        ]

    def delete(self, using=None, keep_parents=False):
        """Override delete method to perform soft delete."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        """Perform actual database deletion."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore a soft-deleted object."""
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class UUIDModel(models.Model):
    """
    Abstract base model that uses UUID as primary key instead of integer.
    
    UUIDs are globally unique and prevent enumeration attacks that can
    occur with sequential integer primary keys.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
        help_text="Universally unique identifier for this object"
    )

    class Meta:
        abstract = True


class ActiveModel(TimeStampedModel):
    """
    Abstract base model that provides active/inactive status management.
    
    This is useful for models that need to be temporarily disabled without
    being deleted, such as credentials, registries, etc.
    """
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Indicates whether this object is currently active"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def activate(self):
        """Mark the object as active."""
        self.is_active = True
        self.save()

    def deactivate(self):
        """Mark the object as inactive."""
        self.is_active = False
        self.save()


class MetadataModel(TimeStampedModel):
    """
    Abstract base model that provides JSON metadata storage.
    
    This allows for flexible, extensible data storage without requiring
    schema changes for additional metadata fields.
    """
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadata",
        help_text="Additional metadata stored as JSON"
    )

    class Meta:
        abstract = True

    def get_metadata(self, key, default=None):
        """Get a specific metadata value by key."""
        return self.metadata.get(key, default)

    def set_metadata(self, key, value):
        """Set a specific metadata value by key."""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
        self.save()

    def remove_metadata(self, key):
        """Remove a specific metadata key."""
        if self.metadata and key in self.metadata:
            del self.metadata[key]
            self.save()


class ExpirableModel(TimeStampedModel):
    """
    Abstract base model that provides expiration functionality.
    
    Useful for models that should expire after a certain time,
    such as build outputs, temporary credentials, etc.
    """
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expires At",
        help_text="Timestamp when this object expires"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['expires_at']),
        ]

    @property
    def is_expired(self):
        """Check if the object has expired."""
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at

    def set_expiration(self, hours=None, days=None, expires_at=None):
        """Set expiration time for the object."""
        if expires_at:
            self.expires_at = expires_at
        elif hours:
            self.expires_at = timezone.now() + timezone.timedelta(hours=hours)
        elif days:
            self.expires_at = timezone.now() + timezone.timedelta(days=days)
        else:
            raise ValueError("Must specify hours, days, or expires_at")
        self.save()


class AuditModel(TimeStampedModel):
    """
    Abstract base model that provides audit trail functionality.
    
    Tracks when objects are created, updated, and by whom (if user is available).
    """
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name="Created By",
        help_text="User who created this object"
    )
    updated_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name="Last Updated By",
        help_text="User who last updated this object"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['updated_by']),
        ]

    def save(self, *args, **kwargs):
        """Ensure timestamps are updated on save."""
        from django.contrib.auth import get_user_model
        
        # Try to get current user from thread-local storage
        # This would need to be set in middleware
        if hasattr(self, '_current_user'):
            user = self._current_user
            if user and user.is_authenticated:
                if not self.pk:  # New object
                    self.created_by = user
                self.updated_by = user
        
        super().save(*args, **kwargs)


class BaseNameModel(TimeStampedModel):
    """
    Abstract base model for objects that have a name and need basic functionality.
    
    Combines timestamp tracking, active status, and name fields commonly
    used across many models in the application.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name="Name",
        help_text="Unique name for this object"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Indicates whether this object is currently active"
    )

    class Meta:
        abstract = True


class TimestampedMetadataModel(TimeStampedModel):
    """
    Abstract base model combining timestamp tracking and metadata.
    """
    metadata = models.JSONField(default=dict, blank=True, help_text="JSON metadata for the object")
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]


class TimestampedExpirableModel(TimeStampedModel):
    """
    Abstract base model combining timestamp tracking and expiration.
    """
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expires At",
        help_text="Timestamp when this object expires"
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['expires_at']),
        ]
    
    @property
    def is_expired(self) -> bool:
        """Check if the object has expired."""
        if self.expires_at is None:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at


class BaseDescriptionModel(BaseNameModel):
    """
    Abstract base model for objects that have a name and description.
    
    Extends BaseNameModel with a description field for objects that
    need additional textual information.
    """
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Detailed description of this object"
    )

    class Meta:
        abstract = True
