
"""
Django models for pipeline execution and build management.

This module contains PipelineRun and BuildOutput models for tracking
the execution of build pipelines and the artifacts they produce.
"""

import os
import uuid
import hashlib
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import (TimeStampedModel, ExpirableModel, MetadataModel,
                             TimestampedMetadataModel, TimestampedExpirableModel)
from apps.repositories.models import GitRepository
from apps.registries.models import ContainerRegistry


class PipelineStatus(models.TextChoices):
    """Enumeration of pipeline execution statuses."""
    
    PENDING = 'pending', _('Pending')
    QUEUED = 'queued', _('Queued')
    RUNNING = 'running', _('Running')
    COMPLETED = 'completed', _('Completed')
    FAILED = 'failed', _('Failed')
    CANCELLED = 'cancelled', _('Cancelled')
    TIMEOUT = 'timeout', _('Timeout')
    
    # Progress-specific statuses
    CLONING = 'cloning', _('Cloning Repository')
    BUILDING = 'building', _('Building')
    PACKAGING = 'packaging', _('Packaging')
    PUSHING = 'pushing', _('Pushing to Registry')


class OutputType(models.TextChoices):
    """Enumeration of pipeline output types."""
    
    ZIP_FILE = 'zip', _('ZIP File')
    DOCKER_IMAGE = 'docker_image', _('Docker Image')


class BuildStatus(models.TextChoices):
    """Enumeration of build output statuses."""
    
    PENDING = 'pending', _('Pending')
    AVAILABLE = 'available', _('Available')
    EXPIRED = 'expired', _('Expired')
    DELETED = 'deleted', _('Deleted')


def get_pipeline_log_path(instance, filename):
    """
    Generate storage path for pipeline log files.
    """
    return f"pipeline_logs/{instance.pk}/{filename}"


def get_build_output_path(instance, filename):
    """
    Generate storage path for build output files.
    """
    if instance.output_type == OutputType.ZIP_FILE:
        safe_filename = f"build_output_{instance.pk}_{uuid.uuid4().hex[:8]}"
        extension = 'zip'
        return f"build_outputs/{instance.pipeline_run.pk}/{safe_filename}.{extension}"
    return filename


class PipelineRun(TimestampedMetadataModel):
    """
    Represents a single execution of the build pipeline.
    
    This model tracks the complete lifecycle of a custom Open WebUI build,
    from repository cloning through to final artifact generation and optional
    container registry pushing.
    
    Inherits from:
    - TimeStampedModel: provides created_at, updated_at timestamps
    - MetadataModel: provides JSON metadata field
    """
    status = models.CharField(
        max_length=20,
        choices=PipelineStatus.choices,
        default=PipelineStatus.PENDING,
        verbose_name="Status",
        help_text="Current execution status"
    )
    steps_to_execute = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Steps to Execute",
        help_text="List of pipeline steps to execute"
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Started At",
        help_text="Timestamp when execution started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Completed At",
        help_text="Timestamp when execution completed or failed"
    )
    logs = models.TextField(
        blank=True,
        verbose_name="Execution Logs",
        help_text="Complete execution logs"
    )
    log_file = models.FileField(
        upload_to=get_pipeline_log_path,
        null=True,
        blank=True,
        max_length=1024,
        verbose_name="Log File",
        help_text="Log file for detailed execution information"
    )
    
    # Source configuration
    git_repository = models.ForeignKey(
        GitRepository,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pipeline_runs',
        verbose_name="Git Repository",
        help_text="Source Git repository for the build"
    )
    branch = models.CharField(
        max_length=255,
        default='main',
        verbose_name="Branch",
        help_text="Git branch to build from"
    )
    commit_hash = models.CharField(
        max_length=40,
        blank=True,
        verbose_name="Commit Hash",
        help_text="Specific commit hash to build"
    )
    
    # Output configuration
    output_type = models.CharField(
        max_length=20,
        choices=OutputType.choices,
        default=OutputType.ZIP_FILE,
        verbose_name="Output Type",
        help_text="Type of build output to generate (ZIP is prioritized for simplicity)"
    )
    registry = models.ForeignKey(
        ContainerRegistry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pipeline_runs',
        verbose_name="Container Registry",
        help_text="Registry to push Docker images to (only required for Docker Image output)"
    )
    image_tag = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Image Tag",
        help_text="Custom tag for Docker images (only required for Docker Image output)"
    )
    
    # Execution tracking
    worker_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Worker ID",
        help_text="ID of the worker processing this pipeline"
    )
    progress_percentage = models.PositiveIntegerField(
        default=0,
        verbose_name="Progress Percentage",
        help_text="Execution progress (0-100)"
    )
    current_step = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Current Step",
        help_text="Currently executing pipeline step"
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="Error Message",
        help_text="Details about execution failure"
    )
    
    # Configuration
    branding_template_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Branding Template ID",
        help_text="ID of branding template to apply"
    )
    build_arguments = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Build Arguments",
        help_text="Additional arguments for the build process"
    )
    environment_variables = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Environment Variables",
        help_text="Environment variables for the build"
    )
    
    class Meta:
        verbose_name = "Pipeline Run"
        verbose_name_plural = "Pipeline Runs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['started_at']),
            models.Index(fields=['completed_at']),
            models.Index(fields=['git_repository']),
            models.Index(fields=['registry']),
            models.Index(fields=['output_type']),
            models.Index(fields=['worker_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Pipeline Run #{self.pk} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to handle timestamp and status validation."""
        # Update timestamps based on status changes
        if not self.pk:
            # New pipeline run
            if self.status in [PipelineStatus.RUNNING, PipelineStatus.CLONING, 
                             PipelineStatus.BUILDING, PipelineStatus.PACKAGING, 
                             PipelineStatus.PUSHING]:
                self.started_at = timezone.now()
        else:
            # Existing pipeline run - check status transition
            try:
                old_instance = PipelineRun.objects.get(pk=self.pk)
                old_status = old_instance.status
                
                # Status transition to running
                if (old_status in [PipelineStatus.PENDING, PipelineStatus.QUEUED] and 
                    self.status in [PipelineStatus.RUNNING, PipelineStatus.CLONING,
                                   PipelineStatus.BUILDING, PipelineStatus.PACKAGING, 
                                   PipelineStatus.PUSHING]):
                    if not self.started_at:
                        self.started_at = timezone.now()
                
                # Status transition to terminal state
                if (old_status not in [PipelineStatus.COMPLETED, PipelineStatus.FAILED, 
                                     PipelineStatus.CANCELLED, PipelineStatus.TIMEOUT] and 
                    self.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED,
                                   PipelineStatus.CANCELLED, PipelineStatus.TIMEOUT]):
                    self.completed_at = timezone.now()
                    # Update progress to 100% or 0% based on status
                    self.progress_percentage = 100 if self.status == PipelineStatus.COMPLETED else 0
                    
            except PipelineRun.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
    
    def start_execution(self, worker_id=None):
        """
        Mark the pipeline as started and set worker ID.
        
        Args:
            worker_id (str): ID of the worker executing this pipeline
        """
        self.status = PipelineStatus.RUNNING
        self.started_at = timezone.now()
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.progress_percentage = 0
        self.save(update_fields=['status', 'started_at', 'worker_id', 'progress_percentage'])
    
    def update_progress(self, percentage, current_step=None, message=None):
        """
        Update the execution progress.
        
        Args:
            percentage (int): Progress percentage (0-100)
            current_step (str): Name of current step
            message (str): Optional status message
        """
        self.progress_percentage = max(0, min(100, percentage))
        
        if current_step:
            # Update status based on step
            step_mapping = {
                'clone': PipelineStatus.CLONING,
                'build': PipelineStatus.BUILDING,
                'package': PipelineStatus.PACKAGING,
                'push': PipelineStatus.PUSHING,
            }
            
            normalized_step = current_step.lower().split()[0]
            if normalized_step in step_mapping:
                self.status = step_mapping[normalized_step]
            self.current_step = current_step
        
        if message:
            self.add_log(message)
        
        self.save(update_fields=['progress_percentage', 'status', 'current_step'])
    
    def complete_execution(self, success=True, error_message=None):
        """
        Mark the pipeline as completed.
        
        Args:
            success (bool): Whether execution succeeded
            error_message (str): Error message if failed
        """
        if success:
            self.status = PipelineStatus.COMPLETED
            self.progress_percentage = 100
            self.error_message = ''
            self.add_log("Pipeline execution completed successfully")
        else:
            self.status = PipelineStatus.FAILED
            self.error_message = error_message or "Execution failed"
            self.add_log(f"Pipeline execution failed: {error_message}")
        
        self.completed_at = timezone.now()
        self.current_step = ''
        self.save(update_fields=[
            'status', 'completed_at', 'progress_percentage',
            'error_message', 'current_step'
        ])
    
    def cancel_execution(self, reason=None):
        """
        Cancel the pipeline execution.
        
        Args:
            reason (str): Reason for cancellation
        """
        self.status = PipelineStatus.CANCELLED
        self.completed_at = timezone.now()
        if reason:
            self.error_message = f"Cancelled: {reason}"
            self.add_log(f"Pipeline cancelled: {reason}")
        else:
            self.add_log("Pipeline cancelled")
        
        self.save(update_fields=['status', 'completed_at', 'error_message'])
    
    def add_log(self, message):
        """
        Add a message to the execution logs.
        
        Args:
            message (str): Log message to add
        """
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        
        if self.logs:
            self.logs += f"\n{log_entry}"
        else:
            self.logs = log_entry
        
        # Also update log file if it exists
        if self.log_file and default_storage.exists(self.log_file.name):
            try:
                # Read existing content
                content = default_storage.open(self.log_file.name, 'r').read()
                content = content.decode('utf-8') if isinstance(content, bytes) else content
                
                # Append new entry
                new_content = content + f"\n{log_entry}"
                
                # Write back
                self.log_file.save(self.log_file.name, new_content, save=False)
            except Exception:
                # If file operations fail, just continue with in-memory logs
                pass
    
    def get_execution_duration(self):
        """
        Get the total execution duration.
        
        Returns:
            timedelta: Total execution time or None if not completed
        """
        if not self.started_at:
            return None
        
        end_time = self.completed_at or timezone.now()
        return end_time - self.started_at
    
    @property
    def is_running(self):
        """Check if the pipeline is currently running."""
        return self.status in [
            PipelineStatus.RUNNING, PipelineStatus.CLONING,
            PipelineStatus.BUILDING, PipelineStatus.PACKAGING, PipelineStatus.PUSHING
        ]
    
    @property
    def is_completed(self):
        """Check if the pipeline has reached a terminal state."""
        return self.status in [
            PipelineStatus.COMPLETED, PipelineStatus.FAILED,
            PipelineStatus.CANCELLED, PipelineStatus.TIMEOUT
        ]
    
    @property
    def can_be_cancelled(self):
        """Check if the pipeline can be cancelled."""
        return self.status in [
            PipelineStatus.PENDING, PipelineStatus.QUEUED,
            PipelineStatus.RUNNING, PipelineStatus.CLONING,
            PipelineStatus.BUILDING, PipelineStatus.PACKAGING, PipelineStatus.PUSHING
        ]
    
    def get_build_outputs(self):
        """Get all build outputs for this pipeline run."""
        return self.build_outputs.all()
    
    def get_successful_outputs(self):
        """Get successful build outputs."""
        return self.build_outputs.filter(status=BuildStatus.AVAILABLE)
    
    @classmethod
    def get_running_pipelines(cls):
        """Get all currently running pipelines."""
        return cls.filter(status__in=[
            PipelineStatus.RUNNING, PipelineStatus.CLONING,
            PipelineStatus.BUILDING, PipelineStatus.PACKAGING, PipelineStatus.PUSHING
        ])
    
    @classmethod
    def get_failed_pipelines(cls, hours=24):
        """Get failed pipelines from the last N hours."""
        since = timezone.now() - timedelta(hours=hours)
        return cls.filter(
            status=PipelineStatus.FAILED,
            completed_at__gte=since
        )


class BuildOutput(TimestampedExpirableModel):
    """
    Represents a build artifact produced by a pipeline run.
    
    This model tracks generated files and images, including their location,
    size, checksum, and download statistics.
    
    Inherits from:
    - TimestampedExpirableModel: provides timestamp, expiration functionality
    """
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadata",
        help_text="Additional metadata stored as JSON"
    )
    pipeline_run = models.ForeignKey(
        PipelineRun,
        on_delete=models.CASCADE,
        related_name='build_outputs',
        verbose_name="Pipeline Run",
        help_text="Pipeline run that produced this output"
    )
    output_type = models.CharField(
        max_length=20,
        choices=OutputType.choices,
        verbose_name="Output Type",
        help_text="Type of build output"
    )
    status = models.CharField(
        max_length=20,
        choices=BuildStatus.choices,
        default=BuildStatus.PENDING,
        verbose_name="Status",
        help_text="Current status of the build output"
    )
    file_path = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
        verbose_name="File Path",
        help_text="Path to the generated file (for ZIP/TARBALL outputs)"
    )
    file = models.FileField(
        upload_to=get_build_output_path,
        null=True,
        blank=True,
        max_length=1024,
        verbose_name="File",
        help_text="Generated file (for downloadable outputs)"
    )
    file_size_bytes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="File Size",
        help_text="File size in bytes"
    )
    image_url = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
        verbose_name="Image URL",
        help_text="Docker image URL (for image outputs)"
    )
    checksum_sha256 = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="SHA256 Checksum",
        help_text="SHA256 checksum of the output file"
    )
    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Download Count",
        help_text="Number of times this output has been downloaded"
    )
    build_metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Build Metadata",
        help_text="Additional metadata about the build"
    )
    
    class Meta:
        verbose_name = "Build Output"
        verbose_name_plural = "Build Outputs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pipeline_run']),
            models.Index(fields=['output_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
        unique_together = [
            ['pipeline_run', 'output_type']
        ]
    
    def __str__(self):
        return f"Build Output #{self.pk} ({self.get_output_type_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to handle file metadata and checksums."""
        # Calculate file size and checksum if file is provided
        if self.file and not self.file_size_bytes:
            self.file_size_bytes = self.file.size
            
            # Calculate SHA256 checksum
            self.checksum_sha256 = self._calculate_checksum()
        
        # Set status based on availability
        if self.file or self.image_url:
            if self.status == BuildStatus.PENDING:
                self.status = BuildStatus.AVAILABLE
        
        super().save(*args, **kwargs)
    
    def _calculate_checksum(self):
        """
        Calculate SHA256 checksum of the file.
        
        Returns:
            str: SHA256 checksum as hex string
        """
        if not self.file:
            return None
        
        try:
            hash_sha256 = hashlib.sha256()
            
            # Read file in chunks to handle large files
            with default_storage.open(self.file.name, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_sha256.update(chunk)
            
            return hash_sha256.hexdigest()
            
        except Exception:
            return None
    
    def mark_as_available(self):
        """Mark this build output as available."""
        self.status = BuildStatus.AVAILABLE
        self.save(update_fields=['status'])
    
    def mark_as_expired(self):
        """Mark this build output as expired."""
        self.status = BuildStatus.EXPIRED
        self.save(update_fields=['status'])
    
    def record_download(self):
        """Record a download of this build output."""
        self.download_count += 1
        self.save(update_fields=['download_count'])
    
    def get_file_url(self):
        """
        Get the public URL of the file.
        
        Returns:
            str: File URL or None if no file
        """
        if self.file:
            return self.file.url
        return None
    
    def get_file_name(self):
        """
        Get a user-friendly file name.
        
        Returns:
            str: File name for download
        """
        if self.file:
            return os.path.basename(self.file.name)
        
        # Generate a name based on pipeline run info
        timestamp = self.created_at.strftime('%Y%m%d_%H%M%S')
        pipeline_id = self.pipeline_run.pk
        
        if self.output_type == OutputType.ZIP_FILE:
            return f"custom_webui_build_{pipeline_id}_{timestamp}.zip"
        else:
            return f"custom_webui_build_{pipeline_id}_{timestamp}"
    
    def get_human_file_size(self):
        """
        Get human-readable file size.
        
        Returns:
            str: Human-readable file size
        """
        if not self.file_size_bytes:
            return "Unknown"
        
        size = self.file_size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def is_available(self):
        """Check if this output is available for download."""
        return (self.status == BuildStatus.AVAILABLE and
                not self.is_expired)
    
    @property
    def can_be_downloaded(self):
        """Check if this output can be downloaded."""
        return self.is_available and (self.file is not None)
    
    def cleanup(self):
        """
        Clean up the output file and mark as deleted.
        
        Returns:
            bool: True if cleanup was successful
        """
        try:
            # Delete the file if it exists
            if self.file and default_storage.exists(self.file.name):
                default_storage.delete(self.file.name)
            
            # Mark as deleted
            self.status = BuildStatus.DELETED
            self.save(update_fields=['status'])
            
            return True
            
        except Exception:
            return False
    
    @classmethod
    def get_available_outputs(cls, output_type=None):
        """
        Get all available build outputs.
        
        Args:
            output_type (str): Filter by output type
            
        Returns:
            QuerySet: Available build outputs
        """
        outputs = cls.filter(status=BuildStatus.AVAILABLE)
        
        if output_type:
            outputs = outputs.filter(output_type=output_type)
        
        return outputs
    
    @classmethod
    def cleanup_expired_outputs(cls):
        """
        Clean up all expired build outputs.
        
        Returns:
            tuple: (count_cleaned, count_failed)
        """
        expired = cls.filter(
            expires_at__lt=timezone.now(),
            status=BuildStatus.AVAILABLE
        )
        
        cleaned = 0
        failed = 0
        
        for output in expired:
            if output.cleanup():
                cleaned += 1
            else:
                failed += 1
        
        return cleaned, failed


# Signal receivers
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

@receiver(post_save, sender=PipelineRun)
def pipeline_run_saved(sender, instance, created, **kwargs):
    """Handle post-save actions for PipelineRun."""
    if created:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Pipeline Run #{instance.pk} created with status '{instance.status}'")

@receiver(post_save, sender=BuildOutput)
def build_output_saved(sender, instance, created, **kwargs):
    """Handle post-save actions for BuildOutput."""
    if created:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Build Output #{instance.pk} created for pipeline #{instance.pipeline_run.pk}")

@receiver(pre_delete, sender=BuildOutput)
def build_output_deleted(sender, instance, **kwargs):
    """Handle cleanup when a BuildOutput is deleted."""
    # Delete the actual file
    if instance.file and default_storage.exists(instance.file.name):
        default_storage.delete(instance.file.name)


# Fix PipelineRun manager reference
PipelineRun.add_to_class('objects', models.Manager())
