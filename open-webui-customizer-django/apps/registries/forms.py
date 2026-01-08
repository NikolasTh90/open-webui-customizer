"""
Django forms for registry management.

This module provides Django forms for creating and updating container registries.
"""

from django import forms

from apps.registries.models import ContainerRegistry, RegistryType


class ContainerRegistryForm(forms.ModelForm):
    """
    Form for creating and updating container registries.
    """

    class Meta:
        model = ContainerRegistry
        fields = [
            'name', 'registry_url', 'registry_type', 'aws_account_id',
            'aws_region', 'repository_name', 'credential', 'metadata'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a unique name for this registry'
            }),
            'registry_url': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://registry.example.com (for generic registries)'
            }),
            'registry_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'aws_account_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'AWS Account ID (for ECR)'
            }),
            'aws_region': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'AWS region (for ECR)'
            }),
            'repository_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Repository name in registry'
            }),
            'credential': forms.Select(attrs={
                'class': 'form-select'
            }),
            'metadata': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional metadata as JSON'
            }),
        }

    def clean_metadata(self):
        """Validate metadata JSON."""
        metadata = self.cleaned_data.get('metadata')
        if metadata:
            try:
                import json
                json.loads(metadata)
            except json.JSONDecodeError:
                raise forms.ValidationError("Metadata must be valid JSON")
        return metadata or '{}'