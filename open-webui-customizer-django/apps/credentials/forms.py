"""
Django forms for credential management.

This module provides Django forms for creating and updating credentials
with proper validation and security measures.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.credentials.models import Credential, CredentialType


class CredentialForm(forms.ModelForm):
    """
    Form for creating and updating credentials.

    Handles credential data encryption and validation.
    """

    credential_data = forms.JSONField(
        widget=forms.Textarea(attrs={
            'rows': 10,
            'placeholder': 'Enter credential data as JSON (e.g., {"username": "user", "password": "pass"})'
        }),
        help_text="Credential data will be encrypted before storage"
    )

    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        }),
        help_text="Optional expiration date for this credential"
    )

    class Meta:
        model = Credential
        fields = [
            'name', 'credential_type', 'credential_data',
            'expires_at', 'metadata'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a unique name for this credential'
            }),
            'credential_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'metadata': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Optional metadata as JSON'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set initial values for datetime-local widget
        if self.instance and self.instance.pk and self.instance.expires_at:
            self.fields['expires_at'].initial = self.instance.expires_at.strftime('%Y-%m-%dT%H:%M')

    def clean_credential_data(self):
        """Validate credential data structure."""
        data = self.cleaned_data['credential_data']
        credential_type = self.cleaned_data.get('credential_type')

        if not isinstance(data, dict):
            raise ValidationError("Credential data must be a valid JSON object")

        if credential_type:
            # Type-specific validation
            if credential_type == CredentialType.GIT_SSH_KEY:
                required_fields = ['private_key']
            elif credential_type == CredentialType.GIT_HTTPS_TOKEN:
                required_fields = ['token']
            elif credential_type == CredentialType.GIT_USERNAME_PASSWORD:
                required_fields = ['username', 'password']
            elif credential_type == CredentialType.AWS_ECR:
                required_fields = ['access_key_id', 'secret_access_key']
            elif credential_type == CredentialType.DOCKER_HUB:
                required_fields = ['username', 'password']
            elif credential_type == CredentialType.QUAY_IO:
                required_fields = ['username', 'password']
            elif credential_type == CredentialType.GENERIC_REGISTRY:
                required_fields = ['username', 'password']
            elif credential_type == CredentialType.API_KEY:
                required_fields = ['api_key']
            elif credential_type == CredentialType.OAUTH_TOKEN:
                required_fields = ['access_token']
            else:
                required_fields = []

            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise ValidationError(
                    f"Missing required fields for {credential_type}: {', '.join(missing_fields)}"
                )

        return data

    def clean_expires_at(self):
        """Validate expiration date."""
        expires_at = self.cleaned_data.get('expires_at')

        if expires_at and expires_at <= timezone.now():
            raise ValidationError("Expiration date must be in the future")

        return expires_at

    def clean_metadata(self):
        """Validate metadata JSON."""
        metadata = self.cleaned_data.get('metadata')

        if metadata and not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a valid JSON object")

        return metadata or {}


class CredentialDataForm(forms.Form):
    """
    Form for updating credential data.

    Requires full credential data for re-encryption.
    """

    credential_data = forms.JSONField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Enter complete credential data as JSON'
        }),
        help_text="Complete credential data required for re-encryption"
    )

    def __init__(self, *args, **kwargs):
        self.credential = kwargs.pop('credential', None)
        super().__init__(*args, **kwargs)

    def clean_credential_data(self):
        """Validate credential data for the specific credential type."""
        data = self.cleaned_data['credential_data']

        if not isinstance(data, dict):
            raise ValidationError("Credential data must be a valid JSON object")

        if self.credential:
            # Validate against the credential's type
            try:
                self.credential._validate_credential_data(data)
            except Exception as e:
                raise ValidationError(str(e))

        return data


class CredentialSearchForm(forms.Form):
    """
    Form for searching and filtering credentials.
    """

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search credentials...'
        })
    )

    credential_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + list(CredentialType.choices),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    include_expired = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Include expired credentials"
    )