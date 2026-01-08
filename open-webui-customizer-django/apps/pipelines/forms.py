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

    branding_template_id = forms.ModelChoiceField(
        queryset=BrandingTemplate.objects.none(),  # Will be set in __init__
        required=False,
        empty_label="No branding (default Open WebUI)",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Branding Template",
        help_text="Optional: Choose a branding template to apply custom logos, colors, and styling"
    )

    class Meta:
        model = PipelineRun
        fields = [
            'git_repository', 'output_type', 'branch', 'registry',
            'image_tag', 'branding_template_id', 'build_arguments',
            'environment_variables', 'metadata'
        ]
        widgets = {
            'git_repository': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'updateRepositoryInfo()'
            }),
            'output_type': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'toggleOutputFields()'
            }),
            'branch': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'main',
                'pattern': '[a-zA-Z0-9/_-]+',
                'title': 'Branch names can only contain letters, numbers, underscores, hyphens, and forward slashes'
            }),
            'registry': forms.Select(attrs={
                'class': 'form-select',
                'id': 'registry-field'
            }),
            'image_tag': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'latest',
                'pattern': '[a-zA-Z0-9._-]+',
                'title': 'Image tags can only contain letters, numbers, dots, underscores, and hyphens',
                'id': 'image-tag-field'
            }),
            'build_arguments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '{"BUILDKIT_INLINE_CACHE": "1", "NODE_ENV": "production"}'
            }),
            'environment_variables': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '{"API_URL": "https://api.example.com", "DEBUG": "false"}'
            }),
            'metadata': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '{"description": "Custom Open WebUI build", "version": "1.0.0"}'
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

        # Set up branding template dropdown
        branding_templates = BrandingTemplate.objects.filter(is_active=True).order_by('-is_default', 'name')
        if not branding_templates.exists():
            # If no templates exist, create a default option that explains the situation
            self.fields['branding_template_id'].queryset = BrandingTemplate.objects.none()
            self.fields['branding_template_id'].empty_label = "No branding templates available - create one first"
        else:
            self.fields['branding_template_id'].queryset = branding_templates
            self.fields['branding_template_id'].empty_label = "No branding (default Open WebUI)"
        self.fields['branding_template_id'].required = False

    def clean_branding_template_id(self):
        """Convert the selected BrandingTemplate instance to its ID."""
        template = self.cleaned_data.get('branding_template_id')
        if template:
            return template.pk
        return None


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

    def clean(self):
        """Validate form dependencies between fields."""
        cleaned_data = super().clean()
        output_type = cleaned_data.get('output_type')
        registry = cleaned_data.get('registry')
        image_tag = cleaned_data.get('image_tag')

        # Validate Docker-specific requirements
        if output_type == OutputType.DOCKER_IMAGE:
            # For Docker images, registry and image tag are strongly recommended
            # but not strictly required (can build locally)
            if not registry and not image_tag:
                # Add a warning but don't prevent submission
                self.add_warning(
                    "Building Docker image without registry and tag. "
                    "The image will only be available locally and won't be pushed to any registry.",
                    code='docker_build_local'
                )

        # Validate ZIP output restrictions
        elif output_type == OutputType.ZIP_FILE:
            # Remove registry and image_tag for ZIP output as they're not needed
            cleaned_data['registry'] = None
            cleaned_data['image_tag'] = ''

        return cleaned_data

    def add_warning(self, message, code=None):
        """Add a warning message to the form."""
        if not hasattr(self, '_warnings'):
            self._warnings = []
        
        # Create a warning similar to ValidationError but for warnings
        from django.core.exceptions import ValidationError
        try:
            # Try to use ValidationError for warning display
            raise ValidationError(message, code=code)
        except ValidationError as e:
            self._warnings.append(str(e))

    def has_warnings(self):
        """Check if the form has any warnings."""
        return hasattr(self, '_warnings') and len(self._warnings) > 0

    def get_warnings(self):
        """Get all warning messages."""
        return getattr(self, '_warnings', [])