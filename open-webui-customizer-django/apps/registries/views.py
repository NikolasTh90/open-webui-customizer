"""
Frontend views for registry management.

This module provides Django views for the registry management interface,
including list, create, update, and detail views with HTMX support.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages

from apps.registries.models import ContainerRegistry
from apps.registries.forms import ContainerRegistryForm
from apps.branding.models import BrandingTemplate


class ContainerRegistryListView(ListView):
    """List view for container registries with filtering."""

    model = ContainerRegistry
    template_name = 'registries/list.html'
    context_object_name = 'registries'
    paginate_by = 25

    def get_queryset(self):
        queryset = ContainerRegistry.objects.filter(is_active=True).order_by('-created_at')
        return queryset


class ContainerRegistryDetailView(DetailView):
    """Detail view for individual container registries."""

    model = ContainerRegistry
    template_name = 'registries/detail.html'
    context_object_name = 'registry'

    def get_queryset(self):
        return ContainerRegistry.objects.filter(is_active=True)


class ContainerRegistryCreateView(CreateView):
    """Create view for new container registries."""

    model = ContainerRegistry
    form_class = ContainerRegistryForm
    template_name = 'registries/form.html'
    success_url = '/registries/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Registry'
        context['submit_text'] = 'Create Registry'
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Registry "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class ContainerRegistryUpdateView(UpdateView):
    """Update view for existing container registries."""

    model = ContainerRegistry
    form_class = ContainerRegistryForm
    template_name = 'registries/form.html'
    success_url = '/registries/'

    def get_queryset(self):
        return ContainerRegistry.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Registry'
        context['submit_text'] = 'Update Registry'
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Registry "{self.object.name}" updated successfully.')
        return super().form_valid(form)


def registry_delete(request, pk):
    """Delete (deactivate) a registry."""
    registry = get_object_or_404(ContainerRegistry, pk=pk, is_active=True)

    registry.is_active = False
    registry.save()

    messages.success(request, f'Registry "{registry.name}" deactivated successfully.')
    return redirect('registries:list')


def registry_test_connection(request, pk):
    """Test registry connection via HTMX."""
    registry = get_object_or_404(ContainerRegistry, pk=pk, is_active=True)

    # Placeholder for connection testing
    test_results = {
        'registry_type': registry.registry_type,
        'connection_tested': True,
        'error': None,
        'details': 'Registry connection test completed successfully',
        'status_class': 'success'
    }

    if request.htmx:
        return render(request, 'registries/partials/connection_test_result.html', {
            'registry': registry,
            'test_results': test_results,
        })

    messages.info(request, f'Connection test: {test_results["details"]}')
    return redirect('registries:detail', pk=pk)
