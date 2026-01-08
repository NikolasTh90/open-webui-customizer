"""
Django admin configuration for credential models.
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

from .models import Credential, CredentialType


@admin.register(Credential)
class CredentialAdmin(ModelAdmin):
    """Admin configuration for Credential model."""
    
    list_display = [
        'name',
        'credential_type',
        'is_active',
        'is_expired',
        'last_used_at',
        'created_at'
    ]
    list_filter = [
        'credential_type',
        'is_active',
        'created_at',
        'last_used_at',
        'expires_at'
    ]
    search_fields = [
        'name',
        'description'
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'encryption_key_id',
        'credential_summary',
        'is_expired'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'credential_type',
                'description',
                'is_active'
            )
        }),
        ('Expiration', {
            'fields': (
                'expires_at',
                'is_expired'
            )
        }),
        ('Usage Tracking', {
            'fields': (
                'last_used_at',
            )
        }),
        ('Security Information', {
            'fields': (
                'encryption_key_id',
                'credential_summary'
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
        'update_last_used',
        'test_credentials'
    ]
    
    def credential_summary(self, obj):
        """Display a summary of the encrypted credential data."""
        try:
            data = obj.get_credential_data()
            summary_parts = []
            
            # Show key fields based on credential type
            if obj.credential_type == CredentialType.GIT_SSH_KEY:
                summary_parts.append(f"Key type: {data.get('key_type', 'rsa')}")
                if data.get('fingerprint'):
                    summary_parts.append(f"Fingerprint: {data['fingerprint'][:16]}...")
            
            elif obj.credential_type in [
                CredentialType.GIT_HTTPS_TOKEN,
                CredentialType.API_KEY,
                CredentialType.OAUTH_TOKEN
            ]:
                token = data.get('token', data.get('api_key', data.get('access_token', '')))
                if token:
                    summary_parts.append(f"Token: {token[:8]}...")
                if data.get('username'):
                    summary_parts.append(f"Username: {data['username']}")
            
            elif obj.credential_type in [
                CredentialType.GIT_USERNAME_PASSWORD,
                CredentialType.DOCKER_HUB,
                CredentialType.QUAY_IO,
                CredentialType.GENERIC_REGISTRY
            ]:
                if data.get('username'):
                    summary_parts.append(f"Username: {data['username']}")
                    summary_parts.append("Password: [encrypted]")
            
            elif obj.credential_type == CredentialType.AWS_ECR:
                if data.get('access_key_id'):
                    summary_parts.append(f"Access Key: {data['access_key_id'][:4]}...")
                    summary_parts.append("Secret Key: [encrypted]")
                if data.get('region'):
                    summary_parts.append(f"Region: {data['region']}")
            
            return mark_safe('<br>'.join(summary_parts)) if summary_parts else 'No data'
            
        except Exception:
            return 'Failed to decrypt'
    credential_summary.short_description = 'Credential Data'
    
    def is_expired(self, obj):
        """Display expiration status with color coding."""
        if obj.expires_at is None:
            return mark_safe('<span style="color: #666;">Never expires</span>')
        
        if obj.is_expired:
            return mark_safe('<span style="color: #d32f2f;">Expired</span>')
        
        # Check if expiring soon (within 7 days)
        days_until_expiry = (obj.expires_at - timezone.now()).days
        if days_until_expiry <= 7:
            return mark_safe(
                f'<span style="color: #f57c00;">Expires in {days_until_expiry} days</span>'
            )
        
        return mark_safe('<span style="color: #388e3c;">Valid</span>')
    is_expired.short_description = 'Expiration Status'
    
    def mark_as_active(self, request, queryset):
        """Mark selected credentials as active."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} credentials marked as active.'
        )
    mark_as_active.short_description = 'Mark selected as active'
    
    def mark_as_inactive(self, request, queryset):
        """Mark selected credentials as inactive."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} credentials marked as inactive.'
        )
    mark_as_inactive.short_description = 'Mark selected as inactive'
    
    def update_last_used(self, request, queryset):
        """Update the last_used_at timestamp for selected credentials."""
        now = timezone.now()
        updated = queryset.update(last_used_at=now)
        self.message_user(
            request,
            f'Last used timestamp updated for {updated} credentials.'
        )
    update_last_used.short_description = 'Update last used timestamp'
    
    def test_credentials(self, request, queryset):
        """Test the selected credentials."""
        from .models import CredentialTestService
        from django.contrib import messages
        
        test_service = CredentialTestService()
        success_count = 0
        failure_count = 0
        
        for credential in queryset:
            try:
                result = test_service.test_credential(credential)
                if result['success']:
                    success_count += 1
                    messages.success(
                        request,
                        f"{credential.name}: {result['message']}"
                    )
                else:
                    failure_count += 1
                    messages.error(
                        request,
                        f"{credential.name}: {result['message']}"
                    )
            except Exception as e:
                failure_count += 1
                messages.error(
                    request,
                    f"{credential.name}: Test failed with error: {str(e)}"
                )
        
        if success_count or failure_count:
            messages.info(
                request,
                f"Test completed: {success_count} passed, {failure_count} failed"
            )
    test_credentials.short_description = 'Test selected credentials'
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize the form based on object state."""
        form = super().get_form(request, obj, **kwargs)
        
        # Hide/disable certain fields for existing objects
        if obj:
            form.base_fields['credential_type'].disabled = True
            form.base_fields['encrypted_data'].disabled = True
        
        return form
    
    def save_model(self, request, obj, form, change):
        """Handle credential encryption on save."""
        if not change:  # New object
            # Handle encrypted data from form
            # This would typically be handled in a custom form or view
            pass
        super().save_model(request, obj, form, change)


# Custom admin site configuration
admin.site.site_header = 'Open WebUI Customizer Administration'
admin.site.site_title = 'Open WebUI Customizer'
admin.site.index_title = 'Welcome to Open WebUI Customizer Administration'
