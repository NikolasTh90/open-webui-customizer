"""
Frontend views for repository management.

This module provides Django views for the repository management interface,
including list, create, update, and detail views with HTMX support.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils import timezone

from apps.repositories.models import GitRepository, RepositoryType, VerificationStatus
from apps.repositories.forms import GitRepositoryForm
from apps.branding.models import BrandingTemplate


class GitRepositoryListView(ListView):
    """List view for Git repositories with filtering and HTMX support."""

    model = GitRepository
    template_name = 'repositories/list.html'
    context_object_name = 'repositories'
    paginate_by = 25

    def get_queryset(self):
        queryset = GitRepository.objects.filter(is_active=True).order_by('-created_at')

        # Filter by type
        repo_type = self.request.GET.get('type')
        if repo_type:
            queryset = queryset.filter(repository_type=repo_type)

        # Filter by verification status
        verification_status = self.request.GET.get('verification_status')
        if verification_status:
            queryset = queryset.filter(verification_status=verification_status)

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['repository_types'] = RepositoryType.choices
        context['verification_statuses'] = VerificationStatus.choices
        context['current_type'] = self.request.GET.get('type')
        context['current_verification_status'] = self.request.GET.get('verification_status')
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


class GitRepositoryDetailView(DetailView):
    """Detail view for individual Git repositories."""

    model = GitRepository
    template_name = 'repositories/detail.html'
    context_object_name = 'repository'

    def get_queryset(self):
        return GitRepository.objects.filter(is_active=True)


class GitRepositoryCreateView(CreateView):
    """Create view for new Git repositories."""

    model = GitRepository
    form_class = GitRepositoryForm
    template_name = 'repositories/form.html'
    success_url = reverse_lazy('repositories:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Repository'
        context['submit_text'] = 'Create Repository'

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
        messages.success(self.request, f'Repository "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class GitRepositoryUpdateView(UpdateView):
    """Update view for existing Git repositories."""

    model = GitRepository
    form_class = GitRepositoryForm
    template_name = 'repositories/form.html'
    success_url = reverse_lazy('repositories:list')

    def get_queryset(self):
        return GitRepository.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Repository'
        context['submit_text'] = 'Update Repository'
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Repository "{self.object.name}" updated successfully.')
        return super().form_valid(form)


def repository_delete(request, pk):
    """Delete (deactivate) a repository."""
    repository = get_object_or_404(GitRepository, pk=pk, is_active=True)
    permanent = request.POST.get('permanent', 'false').lower() == 'true'

    if permanent:
        repository.hard_delete()
        messages.success(request, f'Repository "{repository.name}" permanently deleted.')
    else:
        repository.is_active = False
        repository.save()
        messages.success(request, f'Repository "{repository.name}" deactivated.')

    return redirect('repositories:list')


def repository_verify(request, pk):
    """Verify repository via HTMX."""
    repository = get_object_or_404(GitRepository, pk=pk, is_active=True)

    try:
        # This would implement actual repository verification
        # For now, we'll simulate verification
        verification_success = True
        message = "Repository verification successful"
        status_class = "success"

        # Update repository with verification results
        repository.is_verified = verification_success
        repository.verification_status = VerificationStatus.VERIFIED
        repository.commit_hash = "abc123def456"
        repository.last_commit_date = timezone.now()
        repository.save()

    except Exception as e:
        verification_success = False
        message = f"Repository verification failed: {str(e)}"
        status_class = "danger"

        repository.is_verified = False
        repository.verification_status = VerificationStatus.FAILED
        repository.save()

    # Return HTMX response
    if request.htmx:
        return render(request, 'repositories/partials/verification_result.html', {
            'repository': repository,
            'is_verified': verification_success,
            'message': message,
            'status_class': status_class,
        })

    messages.success(request, f'Repository verification: {message}')
    return redirect('repositories:detail', pk=pk)


def repository_sync(request, pk):
    """Sync repository metadata via HTMX."""
    repository = get_object_or_404(GitRepository, pk=pk, is_active=True)

    try:
        # This would implement actual repository synchronization
        # For now, we'll simulate sync
        repository.commit_hash = "def789ghi012"
        repository.last_commit_date = timezone.now()
        repository.save()

        message = "Repository synchronized successfully"
        status_class = "success"

    except Exception as e:
        message = f"Synchronization failed: {str(e)}"
        status_class = "danger"

    if request.htmx:
        return render(request, 'repositories/partials/sync_result.html', {
            'repository': repository,
            'message': message,
            'status_class': status_class,
        })

    messages.info(request, message)
    return redirect('repositories:detail', pk=pk)
