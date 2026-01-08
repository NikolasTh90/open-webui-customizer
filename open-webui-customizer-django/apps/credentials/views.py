"""
Frontend views for credential management.

This module provides Django views for the credential management interface,
including list, create, update, and detail views with HTMX support.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.template.loader import render_to_string

from apps.credentials.models import Credential, CredentialType
from apps.credentials.forms import CredentialForm, CredentialDataForm
from apps.branding.models import BrandingTemplate


class CredentialListView(ListView):
    """List view for credentials with filtering and HTMX support."""

    model = Credential
    template_name = 'credentials/list.html'
    context_object_name = 'credentials'
    paginate_by = 25

    def get_queryset(self):
        queryset = Credential.objects.filter(is_active=True).order_by('-created_at')

        # Filter by type
        credential_type = self.request.GET.get('type')
        if credential_type:
            queryset = queryset.filter(credential_type=credential_type)

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['credential_types'] = CredentialType.choices
        context['current_type'] = self.request.GET.get('type')
        context['search_query'] = self.request.GET.get('search')

        # Add branding context
        branding_template = BrandingTemplate.objects.filter(is_default=True).first()
        context['branding_template'] = branding_template
        if branding_template:
            context['logo_asset'] = branding_template.brandingasset_set.filter(
                file_type='logo',
                is_active=True
            ).first()
        else:
            context['logo_asset'] = None

        return context


class CredentialDetailView(DetailView):
    """Detail view for individual credentials."""

    model = Credential
    template_name = 'credentials/detail.html'
    context_object_name = 'credential'

    def get_queryset(self):
        return Credential.objects.filter(is_active=True)


class CredentialCreateView(CreateView):
    """Create view for new credentials."""

    model = Credential
    form_class = CredentialForm
    template_name = 'credentials/form.html'
    success_url = reverse_lazy('credentials:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Credential'
        context['submit_text'] = 'Create Credential'

        # Add branding context
        branding_template = BrandingTemplate.objects.filter(is_default=True).first()
        context['branding_template'] = branding_template
        if branding_template:
            context['logo_asset'] = branding_template.brandingasset_set.filter(
                file_type='logo',
                is_active=True
            ).first()
        else:
            context['logo_asset'] = None

        return context

    def form_valid(self, form):
        # Set the credential data
        credential_data = form.cleaned_data.pop('credential_data')
        credential = form.save(commit=False)
        credential.set_credential_data(credential_data)
        credential.save()

        messages.success(self.request, f'Credential "{credential.name}" created successfully.')
        return super().form_valid(form)


class CredentialUpdateView(UpdateView):
    """Update view for existing credentials."""

    model = Credential
    form_class = CredentialForm
    template_name = 'credentials/form.html'
    success_url = reverse_lazy('credentials:list')

    def get_queryset(self):
        return Credential.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Credential'
        context['submit_text'] = 'Update Credential'

        # Add branding context
        branding_template = BrandingTemplate.objects.filter(is_default=True).first()
        context['branding_template'] = branding_template
        if branding_template:
            context['logo_asset'] = branding_template.brandingasset_set.filter(
                file_type='logo',
                is_active=True
            ).first()
        else:
            context['logo_asset'] = None

        return context

    def form_valid(self, form):
        messages.success(self.request, f'Credential "{self.object.name}" updated successfully.')
        return super().form_valid(form)


def credential_delete(request, pk):
    """Delete (deactivate) a credential."""
    credential = get_object_or_404(Credential, pk=pk, is_active=True)
    permanent = request.POST.get('permanent', 'false').lower() == 'true'

    if permanent:
        credential.hard_delete()
        messages.success(request, f'Credential "{credential.name}" permanently deleted.')
    else:
        credential.is_active = False
        credential.save()
        messages.success(request, f'Credential "{credential.name}" deactivated.')

    return redirect('credentials:list')


def credential_verify(request, pk):
    """Verify credential via HTMX."""
    credential = get_object_or_404(Credential, pk=pk, is_active=True)

    try:
        # Basic verification - check if data can be decrypted
        credential_data = credential.get_credential_data()
        is_valid = True
        message = "Credential data is accessible and properly encrypted"
        status_class = "success"
    except Exception as e:
        is_valid = False
        message = f"Credential verification failed: {str(e)}"
        status_class = "danger"

    # Return HTMX response
    if request.htmx:
        return render(request, 'credentials/partials/verification_result.html', {
            'credential': credential,
            'is_valid': is_valid,
            'message': message,
            'status_class': status_class,
        })

    messages.success(request, f'Credential verification: {message}')
    return redirect('credentials:detail', pk=pk)


def credential_test_connection(request, pk):
    """Test credential connection via HTMX."""
    credential = get_object_or_404(Credential, pk=pk, is_active=True)

    # Placeholder for connection testing
    test_results = {
        'credential_type': credential.credential_type,
        'connection_tested': False,
        'error': 'Connection testing not yet implemented',
        'details': None,
        'status_class': 'warning'
    }

    # TODO: Implement actual connection tests based on credential type
    if credential.credential_type == CredentialType.GIT_SSH_KEY:
        test_results.update({
            'details': 'SSH key format validation would be performed',
            'connection_tested': True,
            'status_class': 'info'
        })
    elif credential.credential_type == CredentialType.GIT_HTTPS_TOKEN:
        test_results.update({
            'details': 'HTTPS token format validation would be performed',
            'connection_tested': True,
            'status_class': 'info'
        })
    else:
        test_results['status_class'] = 'secondary'

    if request.htmx:
        return render(request, 'credentials/partials/connection_test_result.html', {
            'credential': credential,
            'test_results': test_results,
        })

    messages.info(request, f'Connection test: {test_results["details"] or test_results["error"]}')
    return redirect('credentials:detail', pk=pk)


def update_credential_data(request, pk):
    """Update credential data via HTMX."""
    credential = get_object_or_404(Credential, pk=pk, is_active=True)

    if request.method == 'POST':
        form = CredentialDataForm(request.POST)
        if form.is_valid():
            credential_data = form.cleaned_data['credential_data']
            credential.set_credential_data(credential_data)
            credential.save()

            if request.htmx:
                return render(request, 'credentials/partials/data_updated.html', {
                    'credential': credential,
                })

            messages.success(request, 'Credential data updated successfully.')
            return redirect('credentials:detail', pk=pk)
    else:
        form = CredentialDataForm()

    if request.htmx:
        return render(request, 'credentials/partials/update_data_form.html', {
            'credential': credential,
            'form': form,
        })

    return render(request, 'credentials/update_data.html', {
        'credential': credential,
        'form': form,
    })
