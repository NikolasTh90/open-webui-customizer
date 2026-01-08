"""
Django forms for branding management.

This module provides Django forms for creating and updating branding templates
and assets with proper validation.
"""

from django import forms

from apps.branding.models import BrandingTemplate, BrandingAsset


class BrandingTemplateForm(forms.ModelForm):
    """
    Form for creating and updating branding templates.
    """

    class Meta:
        model = BrandingTemplate
        fields = [
            'name', 'description', 'brand_name', 'replacement_rules', 'is_default'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a unique name for this template'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description'
            }),
            'brand_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Display name for the brand'
            }),
            'replacement_rules': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Replacement rules as JSON (e.g., {"Open WebUI": "My Custom UI"})'
            }),
        }

    def clean_name(self):
        """Validate template name uniqueness."""
        name = self.cleaned_data['name']

        # Check for uniqueness (excluding current instance if updating)
        queryset = BrandingTemplate.objects.filter(name=name, is_active=True)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError("A branding template with this name already exists")

        return name

    def clean_replacement_rules(self):
        """Validate replacement rules JSON."""
        replacement_rules = self.cleaned_data.get('replacement_rules')
        if replacement_rules:
            try:
                import json
                parsed = json.loads(replacement_rules)
                if not isinstance(parsed, dict):
                    raise forms.ValidationError("Replacement rules must be a valid JSON object")
                return parsed
            except json.JSONDecodeError:
                raise forms.ValidationError("Replacement rules must be valid JSON")
        return {}


class BrandingAssetForm(forms.ModelForm):
    """
    Form for creating and updating branding assets.
    """

    class Meta:
        model = BrandingAsset
        fields = [
            'file_name', 'file_type', 'description', 'template'
        ]
        widgets = {
            'file_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Asset filename (e.g., logo.png)'
            }),
            'file_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional description'
            }),
            'template': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter to active templates
        self.fields['template'].queryset = BrandingTemplate.objects.filter(is_active=True)
