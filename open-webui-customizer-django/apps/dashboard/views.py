"""
Dashboard views for Open WebUI Customizer.

This module provides the main dashboard interface with overview statistics
and quick access to key features.
"""

from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.credentials.models import Credential
from apps.repositories.models import GitRepository
from apps.registries.models import ContainerRegistry
from apps.pipelines.models import PipelineRun, PipelineStatus
from apps.branding.models import BrandingTemplate


class DashboardView(TemplateView):
    """
    Main dashboard view with overview statistics and recent activity.
    """

    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current branding template
        branding_template = BrandingTemplate.objects.filter(is_default=True).first()
        context['branding_template'] = branding_template

        # Get logo asset if branding template exists
        if branding_template:
            context['logo_asset'] = branding_template.assets.filter(
                file_type='logo',
                is_active=True
            ).first()
        else:
            context['logo_asset'] = None

        # Statistics
        context['stats'] = self.get_dashboard_stats()

        # Recent activity
        context['recent_activity'] = self.get_recent_activity()

        # Quick actions
        context['quick_actions'] = self.get_quick_actions()

        return context

    def get_dashboard_stats(self):
        """Get dashboard statistics."""
        now = timezone.now()
        last_30_days = now - timedelta(days=30)

        return {
            'credentials': {
                'total': Credential.objects.filter(is_active=True).count(),
                'expiring_soon': Credential.objects.filter(
                    is_active=True,
                    expires_at__isnull=False,
                    expires_at__lte=now + timedelta(days=30),
                    expires_at__gt=now
                ).count(),
                'expired': Credential.objects.filter(
                    is_active=True,
                    expires_at__isnull=False,
                    expires_at__lte=now
                ).count(),
            },
            'repositories': {
                'total': GitRepository.objects.filter(is_active=True).count(),
                'verified': GitRepository.objects.filter(
                    is_active=True,
                    is_verified=True
                ).count(),
                'unverified': GitRepository.objects.filter(
                    is_active=True,
                    is_verified=False
                ).count(),
            },
            'registries': {
                'total': ContainerRegistry.objects.filter(is_active=True).count(),
            },
            'pipelines': {
                'total': PipelineRun.objects.count(),
                'running': PipelineRun.objects.filter(status=PipelineStatus.RUNNING).count(),
                'completed': PipelineRun.objects.filter(status=PipelineStatus.COMPLETED).count(),
                'failed': PipelineRun.objects.filter(status=PipelineStatus.FAILED).count(),
                'recent_30_days': PipelineRun.objects.filter(
                    created_at__gte=last_30_days
                ).count(),
            },
            'branding': {
                'templates': BrandingTemplate.objects.filter(is_active=True).count(),
                'default_template': BrandingTemplate.objects.filter(is_default=True).first(),
            }
        }

    def get_recent_activity(self):
        """Get recent activity for dashboard."""
        activities = []

        # Recent pipeline runs
        recent_pipelines = PipelineRun.objects.select_related(
            'git_repository', 'registry'
        ).order_by('-created_at')[:5]

        for pipeline in recent_pipelines:
            activities.append({
                'type': 'pipeline',
                'icon': 'fa-cogs',
                'title': f'Pipeline {pipeline.get_status_display()}',
                'description': f'{pipeline.git_repository.name} → {pipeline.registry.name}',
                'timestamp': pipeline.created_at,
                'status': pipeline.status,
                'url': f'/pipelines/{pipeline.id}/'
            })

        # Recent credential updates
        recent_credentials = Credential.objects.order_by('-updated_at')[:3]
        for credential in recent_credentials:
            activities.append({
                'type': 'credential',
                'icon': 'fa-key',
                'title': f'Credential Updated',
                'description': credential.name,
                'timestamp': credential.updated_at,
                'status': 'info',
                'url': f'/credentials/{credential.id}/'
            })

        # Recent repository verifications
        recent_repos = GitRepository.objects.filter(
            is_verified=True
        ).order_by('-updated_at')[:3]

        for repo in recent_repos:
            activities.append({
                'type': 'repository',
                'icon': 'fa-code-branch',
                'title': f'Repository Verified',
                'description': repo.name,
                'timestamp': repo.updated_at,
                'status': 'success',
                'url': f'/repositories/{repo.id}/'
            })

        # Sort by timestamp and return top 10
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:10]

    def get_quick_actions(self):
        """Get quick actions for dashboard."""
        actions = []

        # Check if user needs to set up credentials
        if Credential.objects.filter(is_active=True).count() == 0:
            actions.append({
                'title': 'Add Your First Credential',
                'description': 'Set up Git or registry credentials to get started',
                'icon': 'fa-key',
                'url': '/credentials/create/',
                'color': 'primary',
                'priority': 'high'
            })

        # Check if user needs to add repositories
        if GitRepository.objects.filter(is_active=True).count() == 0:
            actions.append({
                'title': 'Add a Git Repository',
                'description': 'Connect your first repository for customization',
                'icon': 'fa-code-branch',
                'url': '/repositories/create/',
                'color': 'success',
                'priority': 'high'
            })

        # Check if user needs registries
        if ContainerRegistry.objects.filter(is_active=True).count() == 0:
            actions.append({
                'title': 'Configure Container Registry',
                'description': 'Set up where to push your customized images',
                'icon': 'fa-server',
                'url': '/registries/create/',
                'color': 'info',
                'priority': 'medium'
            })

        # Always show create pipeline action
        actions.append({
            'title': 'Start a Pipeline',
            'description': 'Create and run a customization pipeline',
            'icon': 'fa-play',
            'url': '/pipelines/create/',
            'color': 'warning',
            'priority': 'medium'
        })

        # Branding setup
        if BrandingTemplate.objects.filter(is_active=True).count() == 0:
            actions.append({
                'title': 'Create Branding',
                'description': 'Customize the look and feel of your WebUI',
                'icon': 'fa-palette',
                'url': '/branding/create/',
                'color': 'secondary',
                'priority': 'low'
            })

        return sorted(actions, key=lambda x: ['high', 'medium', 'low'].index(x['priority']))


def health_check(request):
    """Simple health check endpoint."""
    return render(request, 'health.html', {
        'status': 'healthy',
        'timestamp': timezone.now(),
    })


def api_root(request):
    """API root page with links to documentation."""
    branding_template = BrandingTemplate.objects.filter(is_default=True).first()
    context = {
        'branding_template': branding_template,
    }

    # Get logo asset if branding template exists
    if branding_template:
        context['logo_asset'] = branding_template.assets.filter(
            file_type='logo',
            is_active=True
        ).first()
    else:
        context['logo_asset'] = None

    return render(request, 'api_root.html', context)
