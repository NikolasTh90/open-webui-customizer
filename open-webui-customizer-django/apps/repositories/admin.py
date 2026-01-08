"""
Django admin configuration for repository models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone

try:
    from unfold.admin import ModelAdmin
    from unfold.decorators import display
except ImportError:
    # Fallback to standard Django admin if unfold is not available
    ModelAdmin = admin.ModelAdmin
    def display(description=None):
        def decorator(func):
            if description:
                func.short_description = description
            return func
        return decorator

from .models import GitRepository, RepositoryType, VerificationStatus


@admin.register(GitRepository)
class GitRepositoryAdmin(ModelAdmin):
    """Admin configuration for GitRepository model."""
    
    list_display = [
        'name',
        'repository_type',
        'is_active',
        'is_verified',
        'verification_status',
        'is_experimental',
        'last_commit_date',
        'created_at'
    ]
    list_filter = [
        'repository_type',
        'is_active',
        'is_verified',
        'verification_status',
        'is_experimental',
        'created_at',
        'last_commit_date'
    ]
    search_fields = [
        'name',
        'repository_url',
        'last_commit_hash'
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'repository_info',
        'verification_info',
        'web_url',
        'repository_identifier',
        'last_commit_info'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'repository_url',
                'repository_type',
                'default_branch',
                'is_active'
            )
        }),
        ('Verification Status', {
            'fields': (
                'is_verified',
                'verification_status',
                'verification_message',
                'verification_info'
            )
        }),
        ('Repository Settings', {
            'fields': (
                'is_experimental',
                'credential'
            )
        }),
        ('Commit Information', {
            'fields': (
                'last_commit_hash',
                'last_commit_date',
                'last_commit_info'
            ),
            'classes': ('collapse',)
        }),
        ('Repository Details', {
            'fields': (
                'repository_info',
                'web_url',
                'repository_identifier'
            ),
            'classes': ('collapse',)
        }),
        ('Local Clone Information', {
            'fields': (
                'clone_path',
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
    
    actions = [
        'mark_as_active',
        'mark_as_inactive',
        'mark_as_experimental',
        'mark_as_production',
        'verify_repositories',
        'test_clone',
        'update_commit_info',
        'cleanup_clones'
    ]
    
    @display(description="Repository Details")
    def repository_info(self, obj):
        """Display formatted repository information."""
        info_parts = []
        
        # Type and URL
        info_parts.append(f"Type: {obj.get_repository_type_display()}")
        info_parts.append(f"URL: {obj.repository_url[:80]}{'...' if len(obj.repository_url) > 80 else ''}")
        
        # Git-formatted URL
        git_url = obj.get_git_url()
        if git_url != obj.repository_url:
            info_parts.append(f"Git URL: {git_url[:80]}{'...' if len(git_url) > 80 else ''}")
        
        # Default branch
        info_parts.append(f"Default Branch: {obj.default_branch}")
        
        # Clone directory
        clone_dir = obj.get_clone_directory()
        info_parts.append(f"Clone Dir: {clone_dir}")
        
        return mark_safe('<br>'.join(info_parts))
    
    @display(description="Verification Status")
    def verification_info(self, obj):
        """Display verification status with color coding."""
        status_colors = {
            VerificationStatus.VERIFIED: '#388e3c',
            VerificationStatus.FAILED: '#d32f2f',
            VerificationStatus.PENDING: '#f57c00',
            VerificationStatus.DISABLED: '#666666'
        }
        
        color = status_colors.get(obj.verification_status, '#666666')
        
        return mark_safe(
            f'<span style="color: {color};">{obj.get_verification_status_display()}</span><br>'
            f'<small>{obj.verification_message or "No verification message"}</small>'
        )
    
    @display(description="Web URL")
    def web_url(self, obj):
        """Display the web URL as a clickable link."""
        url = obj.get_web_url()
        if url:
            return format_html(
                '<a href="{0}" target="_blank">{0}</a>',
                url
            )
        return 'N/A'
    
    @display(description="Repository ID")
    def repository_identifier(self, obj):
        """Display the repository identifier."""
        identifier = obj.get_repository_identifier()
        return mark_safe(
            f'<code style="background: #f5f5f5; padding: 2px 5px;">{identifier}</code>'
        )
    
    @display(description="Last Commit")
    def last_commit_info(self, obj):
        """Display information about the last commit."""
        if obj.last_commit_hash:
            info_parts = []
            
            # Short hash
            short_hash = obj.last_commit_hash[:8]
            info_parts.append(f"Hash: <code>{short_hash}</code>")
            
            # Date
            if obj.last_commit_date:
                info_parts.append(
                    f"Date: {obj.last_commit_date.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            
            return mark_safe('<br>'.join(info_parts))
        
        return 'No commit information'
    
    def mark_as_experimental(self, request, queryset):
        """Mark selected repositories as experimental."""
        updated = queryset.update(is_experimental=True)
        self.message_user(
            request,
            f'{updated} repositories marked as experimental.'
        )
    mark_as_experimental.short_description = 'Mark selected as experimental'
    
    def mark_as_production(self, request, queryset):
        """Mark selected repositories as production-ready."""
        updated = queryset.update(is_experimental=False)
        self.message_user(
            request,
            f'{updated} repositories marked as production-ready.'
        )
    mark_as_production.short_description = 'Mark selected as production-ready'
    
    def verify_repositories(self, request, queryset):
        """Verify the selected repositories."""
        success_count = 0
        failure_count = 0
        
        for repository in queryset:
            try:
                result = repository.verify_repository(force=True)
                if result['success']:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                failure_count += 1
                repository.verification_status = VerificationStatus.FAILED
                repository.verification_message = f"Verification failed: {str(e)}"
                repository.is_verified = False
                repository.save(
                    update_fields=[
                        'verification_status',
                        'verification_message',
                        'is_verified'
                    ]
                )
        
        if success_count or failure_count:
            self.message_user(
                request,
                f"Verification completed: {success_count} passed, {failure_count} failed"
            )
    verify_repositories.short_description = 'Verify selected repositories'
    
    def test_clone(self, request, queryset):
        """Test cloning the selected repositories."""
        from django.contrib import messages
        
        success_count = 0
        failure_count = 0
        
        for repository in queryset:
            try:
                result = repository.test_clone()
                if result['success']:
                    success_count += 1
                    messages.success(
                        request,
                        f"{repository.name}: Clone test successful"
                    )
                else:
                    failure_count += 1
                    messages.error(
                        request,
                        f"{repository.name}: Clone test failed - {result['message']}"
                    )
            except Exception as e:
                failure_count += 1
                messages.error(
                    request,
                    f"{repository.name}: Test failed with error: {str(e)}"
                )
        
        if success_count or failure_count:
            messages.info(
                request,
                f"Clone tests completed: {success_count} passed, {failure_count} failed"
            )
    test_clone.short_description = 'Test clone selected repositories'
    
    def update_commit_info(self, request, queryset):
        """Update commit information for selected repositories."""
        success_count = 0
        failure_count = 0
        
        for repository in queryset:
            if repository.update_commit_info():
                success_count += 1
            else:
                failure_count += 1
        
        if success_count or failure_count:
            self.message_user(
                request,
                f"Commit info updated: {success_count} successful, {failure_count} failed"
            )
    update_commit_info.short_description = 'Update commit information'
    
    def cleanup_clones(self, request, queryset):
        """Clean up local clones for selected repositories."""
        success_count = 0
        failure_count = 0
        
        for repository in queryset:
            if repository.cleanup_clone():
                success_count += 1
            else:
                failure_count += 1
        
        if success_count or failure_count:
            self.message_user(
                request,
                f"Cleanup completed: {success_count} cleaned, {failure_count} failed"
            )
    cleanup_clones.short_description = 'Clean up local clones'
    
    def get_queryset(self, request):
        """Optimize queries for list view."""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('credential')
        return queryset
