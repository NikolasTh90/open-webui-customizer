"""
Django forms for pipeline management.

This module provides Django forms for creating and managing pipeline runs.
"""

from django import forms

from apps.pipelines.models import PipelineRun, PipelineStatus, OutputType
from apps.repositories.models import GitRepository
from apps.registries.models import ContainerRegistry
from apps.branding.models import BrandingTemplate


class PipelineRunForm(forms.ModelForm):
    """
    Form for creating new pipeline runs.

    Handles pipeline configuration and validation.
    """

    class Meta:
        model = PipelineRun
        fields = [
            'git_repository', 'registry', 'output_type', 'branch',
            'image_tag', 'branding_template_id', 'build_arguments',
            'environment_variables', 'steps_to_execute', 'metadata'
        ]
        widgets = {
            'git_repository': forms.Select(attrs={
                'class': 'form-select'
            }),
            'registry': forms.Select(attrs={
                'class': 'form-select'
            }),
            'output_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'branch': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'main'
            }),
            'image_tag': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'latest'
            }),
            'branding_template_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional branding template ID'
            }),
            'build_arguments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Build arguments as JSON'
            }),
            'environment_variables': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Environment variables as JSON'
            }),
            'steps_to_execute': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 4
            }),
            'metadata': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional metadata as JSON'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter to active repositories and registries
        self.fields['git_repository'].queryset = GitRepository.objects.filter(
            is_active=True
        ).order_by('name')

        self.fields['registry'].queryset = ContainerRegistry.objects.filter(
            is_active=True
        ).order_by('name')

        # Set choices for steps
        self.fields['steps_to_execute'].choices = [
            ('clone', 'Clone Repository'),
            ('build', 'Build Application'),
            ('brand', 'Apply Branding'),
            ('push', 'Push to Registry'),
            ('test', 'Run Tests'),
        ]

    def clean_build_arguments(self):
        """Validate build arguments JSON."""
        data = self.cleaned_data.get('build_arguments')
        if data:
            try:
                import json
                json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Build arguments must be valid JSON")
        return data or '{}'

    def clean_environment_variables(self):
        """Validate environment variables JSON."""
        data = self.cleaned_data.get('environment_variables')
        if data:
            try:
                import json
                json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Environment variables must be valid JSON")
        return data or '{}'

    def clean_metadata(self):
        """Validate metadata JSON."""
        data = self.cleaned_data.get('metadata')
        if data:
            try:
                import json
                json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Metadata must be valid JSON")
        return data or '{}'