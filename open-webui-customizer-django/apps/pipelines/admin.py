"""
Django admin configuration for pipeline models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q

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

from .models import PipelineRun, BuildOutput, PipelineStatus, OutputType, BuildStatus


class BuildOutputInline(TabularInline):
    """Inline admin for BuildOutput model."""
    model = BuildOutput
    extra = 0
    fields = [
        'output_type',
        'status',
        'file_size_display',
        'image_url_display',
        'is_available'
    ]
    readonly_fields = [
        'file_size_display',
        'image_url_display',
        'is_available'
    ]
    
    @display(description="Size")
    def file_size_display(self, obj):
        """Display the file size."""
        if obj.file_size_bytes:
            size = obj.file_size_bytes
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        return 'N/A'
    
    @display(description="Image URL")
    def image_url_display(self, obj):
        """Display the image URL."""
        if obj.image_url:
            return mark_safe(
                f'<code style="background: #f5f5f5; padding: 2px 5px;">{obj.image_url[:50]}...</code>'
            )
        return 'N/A'
    
    @display(description="Status")
    def is_available(self, obj):
        """Display availability status."""
        if obj.is_available:
            return mark_safe('<span style="color: #388e3c;">Available</span>')
        elif obj.is_expired:
            return mark_safe('<span style="color: #d32f2f;">Expired</span>')
        else:
            return mark_safe('<span style="color: #f57c00;">Not Available</span>')


@admin.register(PipelineRun)
class PipelineRunAdmin(ModelAdmin):
    """Admin configuration for PipelineRun model."""
    
    list_display = [
        'id',
        'status_with_color',
        'progress_display',
        'git_repository',
        'registry',
        'output_type',
        'created_at',
        'duration'
    ]
    list_filter = [
        'status',
        'output_type',
        'git_repository',
        'registry',
        'created_at',
        'started_at',
        'completed_at'
    ]
    search_fields = [
        'id',
        'worker_id',
        'git_repository__name',
        'registry__name',
        'branch',
        'commit_hash'
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'execution_info',
        'progress_info',
        'duration',
        'logs_display'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'status',
                'output_type',
                'steps_to_execute'
            )
        }),
        ('Source Configuration', {
            'fields': (
                'git_repository',
                'branch',
                'commit_hash'
            )
        }),
        ('Output Configuration', {
            'fields': (
                'registry',
                'image_tag',
                'branding_template_id'
            )
        }),
        ('Execution Information', {
            'fields': (
                'worker_id',
                'progress_percentage',
                'current_step',
                'execution_info',
                'progress_info',
                'duration'
            )
        }),
        ('Build Configuration', {
            'fields': (
                'build_arguments',
                'environment_variables'
            ),
            'classes': ('collapse',)
        }),
        ('Logs', {
            'fields': (
                'logs',
                'log_file',
                'logs_display'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'started_at',
                'completed_at',
                'created_at',
                'updated_at'
            )
        }),
        ('Metadata', {
            'fields': (
                'metadata',
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [BuildOutputInline]
    
    actions = [
        'cancel_pipelines',
        'retry_failed_pipelines',
        'cleanup_logs',
        'mark_as_completed'
    ]
    
    @display(description="Status")
    def status_with_color(self, obj):
        """Display status with color coding."""
        status_colors = {
            PipelineStatus.COMPLETED: '#388e3c',
            PipelineStatus.FAILED: '#d32f2f',
            PipelineStatus.CANCELLED: '#666666',
            PipelineStatus.TIMEOUT: '#f57c00',
            PipelineStatus.RUNNING: '#1976d2',
            PipelineStatus.PENDING: '#666666',
            PipelineStatus.QUEUED: '#f57c00'
        }
        
        color = status_colors.get(obj.status, '#666666')
        
        return mark_safe(
            f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>'
        )
    
    @display(description="Progress")
    def progress_display(self, obj):
        """Display progress as a bar."""
        progress = obj.progress_percentage
        if progress == 0:
            return '0%'
        elif progress == 100:
            return mark_safe(
                '<span style="color: #388e3c; font-weight: bold;">100%</span>'
            )
        else:
            return mark_safe(
                f'<div style="background: #e0e0e0; width: 100px; height: 20px; position: relative;">'
                f'<div style="background: #1976d2; width: {progress}%; height: 100%;"></div>'
                f'<span style="position: absolute; top: 2px; left: 35px; font-size: 12px;">{progress}%</span>'
                f'</div>'
            )
    
    @display(description="Execution Details")
    def execution_info(self, obj):
        """Display execution information."""
        info_parts = []
        
        if obj.worker_id:
            info_parts.append(f"Worker: {obj.worker_id}")
        
        if obj.current_step:
            info_parts.append(f"Current Step: {obj.current_step}")
        
        if obj.error_message:
            info_parts.append(
                f'Error: <span style="color: #d32f2f;">{obj.error_message[:100]}...</span>'
            )
        
        return mark_safe('<br>'.join(info_parts)) if info_parts else 'No execution info'
    
    @display(description="Progress Details")
    def progress_info(self, obj):
        """Display detailed progress information."""
        info_parts = []
        
        info_parts.append(f"Progress: {obj.progress_percentage}%")
        
        if obj.is_running:
            info_parts.append(
                '<span style="color: #1976d2; font-weight: bold;">Currently Running</span>'
            )
        elif obj.is_completed:
            if obj.status == PipelineStatus.COMPLETED:
                info_parts.append(
                    '<span style="color: #388e3c; font-weight: bold;">Completed Successfully</span>'
                )
            else:
                info_parts.append(
                    f'<span style="color: #d32f2f; font-weight: bold;">Completed with {obj.get_status_display()}</span>'
                )
        else:
            info_parts.append(
                '<span style="color: #666666;">Not Started</span>'
            )
        
        return mark_safe('<br>'.join(info_parts))
    
    @display(description="Duration")
    def duration(self, obj):
        """Display the execution duration."""
        duration = obj.get_execution_duration()
        if duration:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        
        if obj.started_at:
            # Still running
            elapsed = timezone.now() - obj.started_at
            total_seconds = int(elapsed.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s (running)"
        
        return 'N/A'
    
    @display(description="Recent Logs")
    def logs_display(self, obj):
        """Display logs with formatting."""
        if obj.logs:
            # Show last few lines
            lines = obj.logs.split('\n')[-10:]
            formatted_lines = []
            for line in lines:
                formatted_lines.append(f'<div style="font-family: monospace; font-size: 12px;">{line}</div>')
            return mark_safe('<div style="background: #f5f5f5; padding: 10px; max-height: 200px; overflow-y: auto;">' + ''.join(formatted_lines) + '</div>')
        return 'No logs'
    
    def cancel_pipelines(self, request, queryset):
        """Cancel selected running pipelines."""
        cancelled = 0
        already_completed = 0
        
        for pipeline in queryset:
            if pipeline.can_be_cancelled:
                pipeline.cancel_execution("Cancelled by admin")
                cancelled += 1
            else:
                already_completed += 1
        
        message_parts = []
        if cancelled:
            message_parts.append(f"{cancelled} pipeline(s) cancelled")
        if already_completed:
            message_parts.append(f"{already_completed} pipeline(s) already completed")
        
        self.message_user(request, ', '.join(message_parts))
    cancel_pipelines.short_description = 'Cancel selected pipelines'
    
    def retry_failed_pipelines(self, request, queryset):
        """Retry failed pipelines."""
        retried = 0
        not_failed = 0
        
        for pipeline in queryset:
            if pipeline.status == PipelineStatus.FAILED:
                # Reset for retry
                pipeline.status = PipelineStatus.PENDING
                pipeline.started_at = None
                pipeline.completed_at = None
                pipeline.progress_percentage = 0
                pipeline.current_step = ''
                pipeline.error_message = ''
                pipeline.save(
                    update_fields=[
                        'status', 'started_at', 'completed_at',
                        'progress_percentage', 'current_step', 'error_message'
                    ]
                )
                retried += 1
            else:
                not_failed += 1
        
        message_parts = []
        if retried:
            message_parts.append(f"{retried} pipeline(s) reset for retry")
        if not_failed:
            message_parts.append(f"{not_failed} pipeline(s) not in failed state")
        
        self.message_user(request, ', '.join(message_parts))
    retry_failed_pipelines.short_description = 'Retry failed pipelines'
    
    def cleanup_logs(self, request, queryset):
        """Clean up logs for selected pipelines."""
        updated = queryset.update(logs='')
        self.message_user(
            request,
            f'Logs cleared for {updated} pipeline(s).'
        )
    cleanup_logs.short_description = 'Clear logs for selected pipelines'
    
    def mark_as_completed(self, request, queryset):
        """Mark selected pipelines as completed."""
        completed = 0
        
        for pipeline in queryset:
            if not pipeline.is_completed:
                pipeline.complete_execution(success=True)
                completed += 1
        
        self.message_user(
            request,
            f'{completed} pipeline(s) marked as completed.'
        )
    mark_as_completed.short_description = 'Mark selected as completed'
    
    def get_queryset(self, request):
        """Optimize queries for list view."""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related(
            'git_repository',
            'registry'
        ).prefetch_related('build_outputs')
        return queryset


@admin.register(BuildOutput)
class BuildOutputAdmin(ModelAdmin):
    """Admin configuration for BuildOutput model."""
    
    list_display = [
        'id',
        'pipeline_run',
        'output_type',
        'status_with_color',
        'file_info',
        'is_available',
        'created_at',
        'expires_at'
    ]
    list_filter = [
        'output_type',
        'status',
        'pipeline_run__status',
        'created_at',
        'expires_at'
    ]
    search_fields = [
        'id',
        'pipeline_run__id',
        'image_url',
        'checksum_sha256'
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'file_details',
        'checksum_info',
        'download_stats'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'pipeline_run',
                'output_type',
                'status'
            )
        }),
        ('File Information', {
            'fields': (
                'file',
                'file_path',
                'file_details',
                'image_url'
            )
        }),
        ('Checksum & Validation', {
            'fields': (
                'checksum_sha256',
                'checksum_info'
            ),
            'classes': ('collapse',)
        }),
        ('Build Metadata', {
            'fields': (
                'build_metadata',
            ),
            'classes': ('collapse',)
        }),
        ('Download Statistics', {
            'fields': (
                'download_count',
                'download_stats'
            )
        }),
        ('Timestamps', {
            'fields': (
                'expires_at',
                'created_at',
                'updated_at'
            )
        }),
        ('Metadata', {
            'fields': (
                'metadata',
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'mark_as_available',
        'mark_as_expired',
        'record_download',
        'cleanup_expired'
    ]
    
    @display(description="Status")
    def status_with_color(self, obj):
        """Display status with color coding."""
        status_colors = {
            BuildStatus.AVAILABLE: '#388e3c',
            BuildStatus.EXPIRED: '#d32f2f',
            BuildStatus.DELETED: '#666666',
            BuildStatus.PENDING: '#f57c00'
        }
        
        color = status_colors.get(obj.status, '#666666')
        
        if obj.is_expired and obj.status == BuildStatus.AVAILABLE:
            color = '#f57c00'
        
        return mark_safe(
            f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>'
        )
    
    @display(description="File/Asset")
    def file_info(self, obj):
        """Display file information."""
        if obj.file:
            size = obj.get_human_file_size()
            return mark_safe(
                f'<a href="{obj.file.url}" target="_blank">Download</a><br>'
                f'Size: {size}'
            )
        elif obj.image_url:
            return mark_safe(
                f'<code>{obj.image_url[:50]}...</code><br>'
                f'<small>Docker image</small>'
            )
        return 'No file'
    
    @display(description="File Details")
    def file_details(self, obj):
        """Display detailed file information."""
        details = []
        
        if obj.file:
            details.append(f"File: {obj.file.name}")
            details.append(f"Size: {obj.get_human_file_size()}")
        
        if obj.file_path:
            details.append(f"Path: {obj.file_path}")
        
        if obj.image_url:
            details.append(f"Image URL: {obj.image_url}")
        
        return mark_safe('<br>'.join(details)) if details else 'No file details'
    
    @display(description="Checksum")
    def checksum_info(self, obj):
        """Display checksum information."""
        if obj.checksum_sha256:
            return mark_safe(
                f'<code style="background: #f5f5f5; padding: 5px; display: inline-block;">{obj.checksum_sha256}</code><br>'
                f'<small>SHA-256 checksum</small>'
            )
        return 'No checksum'
    
    @display(description="Downloads")
    def download_stats(self, obj):
        """Display download statistics."""
        return f"Downloaded {obj.download_count} time(s)"
    
    def mark_as_available(self, request, queryset):
        """Mark selected outputs as available."""
        updated = 0
        for output in queryset:
            if output.status != BuildStatus.DELETED:
                output.mark_as_available()
                updated += 1
        
        self.message_user(
            request,
            f'{updated} output(s) marked as available.'
        )
    mark_as_available.short_description = 'Mark selected as available'
    
    def mark_as_expired(self, request, queryset):
        """Mark selected outputs as expired."""
        updated = queryset.update(status=BuildStatus.EXPIRED)
        self.message_user(
            request,
            f'{updated} output(s) marked as expired.'
        )
    mark_as_expired.short_description = 'Mark selected as expired'
    
    def record_download(self, request, queryset):
        """Record a download for selected outputs."""
        for output in queryset:
            output.record_download()
        
        count = queryset.count()
        self.message_user(
            request,
            f'Download recorded for {count} output(s).'
        )
    record_download.short_description = 'Record download'
    
    def cleanup_expired(self, request, queryset):
        """Clean up expired outputs."""
        cleaned, failed = BuildOutput.cleanup_expired_outputs()
        
        self.message_user(
            request,
            f'Cleanup completed: {cleaned} cleaned, {failed} failed'
        )
    cleanup_expired.short_description = 'Clean up expired outputs'
