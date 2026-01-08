"""
Django admin configuration for registry models.
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

from .models import ContainerRegistry, RegistryType


@admin.register(ContainerRegistry)
class ContainerRegistryAdmin(ModelAdmin):
    """Admin configuration for ContainerRegistry model."""
    
    list_display = [
        'name',
        'registry_type',
        'is_active',
        'is_verified',
        'last_pushed_at',
        'created_at'
    ]
    list_filter = [
        'registry_type',
        'is_active',
        'is_verified',
        'created_at',
        'last_pushed_at'
    ]
    search_fields = [
        'name',
        'repository_name',
        'registry_url',
        'aws_account_id'
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'registry_info',
        'verification_info',
        'docker_login_command'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'registry_type',
                'is_active'
            )
        }),
        ('Registry Configuration', {
            'fields': (
                'registry_url',
                'base_image',
                'target_image',
                'repository_name'
            )
        }),
        ('AWS Configuration', {
            'fields': (
                'aws_account_id',
                'aws_region'
            ),
            'classes': ('collapse',)
        }),
        ('Authentication', {
            'fields': (
                'credential',
            )
        }),
        ('Verification Status', {
            'fields': (
                'is_verified',
                'verification_message',
                'verification_info'
            )
        }),
        ('Usage Information', {
            'fields': (
                'last_pushed_at',
                'docker_login_command'
            ),
            'classes': ('collapse',)
        }),
        ('Registry Information', {
            'fields': (
                'registry_info',
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
        'verify_registries',
        'test_push'
    ]
    
    def registry_info(self, obj):
        """Display formatted registry information."""
        info_parts = []
        
        if obj.registry_type == RegistryType.AWS_ECR:
            registry_url = obj.get_registry_url_for_docker()
            info_parts.append(f"ECR URL: {registry_url}")
            if obj.repository_name:
                info_parts.append(f"Repository: {obj.repository_name}")
        
        elif obj.registry_type == RegistryType.DOCKER_HUB:
            info_parts.append(f"Docker Hub Registry")
            info_parts.append(f"Target: {obj.target_image}")
        
        elif obj.registry_type == RegistryType.QUAY_IO:
            info_parts.append(f"Quay.io Registry")
            info_parts.append(f"Target: {obj.target_image}")
        
        elif obj.registry_type == RegistryType.GENERIC:
            info_parts.append(f"Registry URL: {obj.registry_url}")
        
        return mark_safe('<br>'.join(info_parts))
    registry_info.short_description = 'Registry Details'
    
    def verification_info(self, obj):
        """Display verification status with color coding."""
        if not obj.is_verified:
            return mark_safe(
                f'<span style="color: #d32f2f;">Not Verified</span><br>'
                f'<small>{obj.verification_message or "No verification performed"}</small>'
            )
        
        return mark_safe(
            f'<span style="color: #388e3c;">Verified</span><br>'
            f'<small>{obj.verification_message}</small>'
        )
    verification_info.short_description = 'Verification Status'
    
    def docker_login_command(self, obj):
        """Display the Docker login command."""
        command = obj.get_docker_login_command()
        if command:
            return mark_safe(
                f'<code style="background: #f5f5f5; padding: 5px; '
                f'display: inline-block;">{command}</code>'
            )
        return 'No credential configured'
    docker_login_command.short_description = 'Docker Login Command'
    
    def mark_as_active(self, request, queryset):
        """Mark selected registries as active."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} registries marked as active.'
        )
    mark_as_active.short_description = 'Mark selected as active'
    
    def mark_as_inactive(self, request, queryset):
        """Mark selected registries as inactive."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} registries marked as inactive.'
        )
    mark_as_inactive.short_description = 'Mark selected as inactive'
    
    def verify_registries(self, request, queryset):
        """Verify the selected registries."""
        success_count = 0
        failure_count = 0
        
        for registry in queryset:
            try:
                result = registry.verify_registry(force=True)
                if result['success']:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                failure_count += 1
                registry.is_verified = False
                registry.verification_message = f"Verification failed: {str(e)}"
                registry.save(update_fields=['is_verified', 'verification_message'])
        
        if success_count or failure_count:
            self.message_user(
                request,
                f"Verification completed: {success_count} passed, {failure_count} failed"
            )
    verify_registries.short_description = 'Verify selected registries'
    
    def test_push(self, request, queryset):
        """Test pushing to the selected registries."""
        from django.contrib import messages
        
        success_count = 0
        failure_count = 0
        
        for registry in queryset:
            if not registry.is_verified:
                messages.warning(
                    request,
                    f"Skipped {registry.name}: Registry not verified"
                )
                continue
            
            try:
                result = registry.test_push()
                if result['success']:
                    success_count += 1
                    messages.success(
                        request,
                        f"{registry.name}: Push test successful"
                    )
                else:
                    failure_count += 1
                    messages.error(
                        request,
                        f"{registry.name}: Push test failed - {result['message']}"
                    )
            except Exception as e:
                failure_count += 1
                messages.error(
                    request,
                    f"{registry.name}: Test failed with error: {str(e)}"
                )
        
        if success_count or failure_count:
            messages.info(
                request,
                f"Push tests completed: {success_count} passed, {failure_count} failed"
            )
    test_push.short_description = 'Test push to selected registries'
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize the form based on registry type."""
        form = super().get_form(request, obj, **kwargs)
        
        # Add dynamic field hiding/showing based on registry type
        # This would typically be handled with JavaScript in the admin template
        
        return form
    
    class Media:
        """Custom CSS for admin interface."""
        css = {
            'all': ('admin/css/custom.css',)
        }
