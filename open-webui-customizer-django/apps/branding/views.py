"""
Frontend views for branding management.

This module provides Django views for the branding management interface,
including template and asset management with HTMX support.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages

from apps.branding.models import BrandingTemplate, BrandingAsset
from apps.branding.forms import BrandingTemplateForm, BrandingAssetForm


class BrandingTemplateListView(ListView):
    """List view for branding templates."""

    model = BrandingTemplate
    template_name = 'branding/list.html'
    context_object_name = 'branding_templates'
    paginate_by = 25

    def get_queryset(self):
        queryset = BrandingTemplate.objects.filter(is_active=True).order_by('-created_at')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add branding context
        branding_template = BrandingTemplate.objects.filter(is_default=True).first()
        context['branding_template'] = branding_template
        if branding_template:
            context['logo_asset'] = branding_template.assets.filter(
                file_type='logo',
                is_active=True
            ).first()
        else:
            context['logo_asset'] = None

        return context


class BrandingTemplateDetailView(DetailView):
    """Detail view for individual branding templates."""

    model = BrandingTemplate
    template_name = 'branding/detail.html'
    context_object_name = 'template'

    def get_queryset(self):
        return BrandingTemplate.objects.filter(is_active=True)


class BrandingTemplateCreateView(CreateView):
    """Create view for new branding templates."""

    model = BrandingTemplate
    form_class = BrandingTemplateForm
    template_name = 'branding/form.html'
    success_url = '/branding/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Branding Template'
        context['submit_text'] = 'Create Template'
        return context

    def form_valid(self, form):
        # Save the template first
        response = super().form_valid(form)

        # Handle logo upload
        logo_file = form.cleaned_data.get('logo')
        if logo_file:
            BrandingAsset.objects.create(
                template=form.instance,
                file_name=logo_file.name,
                file_type='logo',
                file=logo_file,
                description='Logo uploaded during template creation'
            )

        messages.success(self.request, f'Branding template "{form.instance.name}" created successfully.')
        return response


class BrandingTemplateUpdateView(UpdateView):
    """Update view for existing branding templates."""

    model = BrandingTemplate
    form_class = BrandingTemplateForm
    template_name = 'branding/form.html'
    success_url = '/branding/'

    def get_queryset(self):
        return BrandingTemplate.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Branding Template'
        context['submit_text'] = 'Update Template'

        # Add current logo asset if exists
        context['current_logo'] = BrandingAsset.objects.filter(
            template=self.object,
            file_type='logo',
            is_active=True
        ).first()

        return context

    def form_valid(self, form):
        # Save the template first
        response = super().form_valid(form)

        # Handle logo upload
        logo_file = form.cleaned_data.get('logo')
        if logo_file:
            # Check if there's an existing logo asset
            existing_logo = BrandingAsset.objects.filter(
                template=form.instance,
                file_type='logo',
                is_active=True
            ).first()

            if existing_logo:
                # Update existing logo
                existing_logo.file = logo_file
                existing_logo.file_name = logo_file.name
                existing_logo.save()
            else:
                # Create new logo asset
                BrandingAsset.objects.create(
                    template=form.instance,
                    file_name=logo_file.name,
                    file_type='logo',
                    file=logo_file,
                    description='Logo uploaded during template update'
                )

        messages.success(self.request, f'Branding template "{self.object.name}" updated successfully.')
        return response


def branding_template_delete(request, pk):
    """Delete (deactivate) a branding template."""
    template = get_object_or_404(BrandingTemplate, pk=pk, is_active=True)

    template.is_active = False
    template.save()

    messages.success(request, f'Branding template "{template.name}" deactivated successfully.')
    return redirect('branding:list')


def set_default_template(request, pk):
    """Set a branding template as the default."""
    template = get_object_or_404(BrandingTemplate, pk=pk, is_active=True)

    # Unset current default
    BrandingTemplate.objects.filter(is_default=True).update(is_default=False)

    # Set new default
    template.is_default = True
    template.save()

    messages.success(request, f'Branding template "{template.name}" set as default.')
    return redirect('branding:detail', pk=pk)


def duplicate_template(request, pk):
    """Create a duplicate of a branding template."""
    template = get_object_or_404(BrandingTemplate, pk=pk, is_active=True)

    # Create new template with copied data
    new_template_data = {
        'name': f"{template.name} (Copy)",
        'description': template.description,
        'brand_name': template.brand_name,
        'replacement_rules': template.replacement_rules.copy() if template.replacement_rules else {},
    }

    new_template = BrandingTemplate.objects.create(**new_template_data)

    # Copy assets (simplified - just create reference, actual file copying would be needed in production)
    for asset in template.assets.all():
        BrandingAsset.objects.create(
            file_name=f"{asset.file_name.rsplit('.', 1)[0]}_copy.{asset.file_name.rsplit('.', 1)[1]}",
            file_type=asset.file_type,
            description=f"Copy of {asset.description}" if asset.description else "",
            template=new_template,
            # Note: In production, would need to copy the actual file
        )

    messages.success(request, f'Branding template "{new_template.name}" created as duplicate.')
    return redirect('branding:detail', pk=new_template.pk)
