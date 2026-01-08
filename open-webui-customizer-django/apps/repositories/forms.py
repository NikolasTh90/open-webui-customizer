"""
Django forms for repository management.

This module provides Django forms for creating and updating Git repositories
with proper validation and security measures.
"""

from django import forms
from django.core.exceptions import ValidationError

from apps.repositories.models import GitRepository, RepositoryType, VerificationStatus
from apps.credentials.models import Credential, CredentialType


class GitRepositoryForm(forms.ModelForm):
    """
    Form for creating and updating Git repositories.

    Handles repository URL validation and credential association.
    """

    class Meta:
        model = GitRepository
        fields = [
            'name', 'repository_url', 'repository_type', 'default_branch',
            'is_experimental', 'credential', 'metadata'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a unique name for this repository'
            }),
            'repository_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://github.com/user/repo or git@github.com:user/repo.git'
            }),
            'repository_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'default_branch': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'main'
            }),
            'credential': forms.Select(attrs={
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

        # Filter credentials to only show Git-related ones
        git_credential_types = [
            CredentialType.GIT_SSH_KEY,
            CredentialType.GIT_HTTPS_TOKEN,
            CredentialType.GIT_USERNAME_PASSWORD,
        ]

        self.fields['credential'].queryset = Credential.objects.filter(
            is_active=True,
            credential_type__in=git_credential_types
        ).order_by('name')

        # Add empty choice for no credential
        self.fields['credential'].empty_label = "No authentication (public repository)"

    def clean_repository_url(self):
        """Validate repository URL format and uniqueness."""
        url = self.cleaned_data['repository_url']
        repository_type = self.cleaned_data.get('repository_type')

        # Basic URL validation
        if not url:
            raise ValidationError("Repository URL is required")

        # Check for uniqueness (excluding current instance if updating)
        queryset = GitRepository.objects.filter(repository_url=url, is_active=True)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise ValidationError("A repository with this URL already exists")

        # Type-specific validation
        if repository_type:
            url_lower = url.lower()

            if repository_type == RepositoryType.GITHUB:
                if 'github.com' not in url_lower:
                    raise ValidationError("GitHub repositories must use github.com domain")
                if not self._is_valid_github_url(url):
                    raise ValidationError("Invalid GitHub repository URL format")

            elif repository_type == RepositoryType.GITLAB:
                if 'gitlab.com' not in url_lower:
                    raise ValidationError("GitLab repositories must use gitlab.com domain")

            elif repository_type == RepositoryType.BITBUCKET:
                if 'bitbucket.org' not in url_lower:
                    raise ValidationError("Bitbucket repositories must use bitbucket.org domain")

        return url

    def clean_name(self):
        """Validate repository name uniqueness."""
        name = self.cleaned_data['name']

        # Check for uniqueness (excluding current instance if updating)
        queryset = GitRepository.objects.filter(name=name, is_active=True)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise ValidationError("A repository with this name already exists")

        return name

    def clean_metadata(self):
        """Validate metadata JSON."""
        metadata = self.cleaned_data.get('metadata')

        if metadata and not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a valid JSON object")

        return metadata or {}

    def _is_valid_github_url(self, url):
        """Check if URL is a valid GitHub repository URL."""
        import re

        # GitHub HTTPS URL pattern
        https_pattern = r'^https?://github\.com/[^/]+/[^/]+(?:\.git)?/?$'

        # GitHub SSH URL pattern
        ssh_pattern = r'^git@github\.com:[^/]+/[^/]+\.git$'

        return bool(re.match(https_pattern, url) or re.match(ssh_pattern, url))


class GitRepositorySearchForm(forms.Form):
    """
    Form for searching and filtering Git repositories.
    """

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search repositories...'
        })
    )

    repository_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + list(RepositoryType.choices),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    verification_status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + list(VerificationStatus.choices),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    include_inactive = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Include inactive repositories"
    )