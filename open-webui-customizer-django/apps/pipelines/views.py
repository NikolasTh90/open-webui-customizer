"""
Frontend views for pipeline management.

This module provides Django views for the pipeline management interface,
including list, create, detail views with HTMX support.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib import messages
from django.urls import reverse_lazy

from apps.pipelines.models import PipelineRun, PipelineStatus
from apps.pipelines.forms import PipelineRunForm


class PipelineRunListView(ListView):
    """List view for pipeline runs with filtering and HTMX support."""

    model = PipelineRun
    template_name = 'pipelines/list.html'
    context_object_name = 'pipelines'
    paginate_by = 25
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by status
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pipeline_statuses'] = PipelineStatus.choices
        context['current_status'] = self.request.GET.get('status')
        return context


class PipelineRunDetailView(DetailView):
    """Detail view for individual pipeline runs."""

    model = PipelineRun
    template_name = 'pipelines/detail.html'
    context_object_name = 'pipeline'


class PipelineRunCreateView(CreateView):
    """Create view for new pipeline runs."""

    model = PipelineRun
    form_class = PipelineRunForm
    template_name = 'pipelines/form.html'
    success_url = reverse_lazy('pipelines:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Pipeline Run'
        context['submit_text'] = 'Start Pipeline'
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Pipeline "{form.instance.name}" started successfully.')
        return super().form_valid(form)


def pipeline_cancel(request, pk):
    """Cancel a running pipeline."""
    pipeline = get_object_or_404(PipelineRun, pk=pk)

    if pipeline.status not in [PipelineStatus.PENDING, PipelineStatus.RUNNING]:
        messages.error(request, 'Can only cancel pending or running pipelines')
        return redirect('pipelines:detail', pk=pk)

    # This would send a cancellation signal to the worker
    pipeline.status = PipelineStatus.FAILED
    pipeline.error_message = 'Pipeline cancelled by user'
    pipeline.save()

    messages.success(request, f'Pipeline "{pipeline.name}" cancelled successfully.')
    return redirect('pipelines:detail', pk=pk)


def pipeline_retry(request, pk):
    """Retry a failed pipeline."""
    pipeline = get_object_or_404(PipelineRun, pk=pk)

    if pipeline.status != PipelineStatus.FAILED:
        messages.error(request, 'Can only retry failed pipelines')
        return redirect('pipelines:detail', pk=pk)

    # Create a new pipeline run with the same parameters
    new_pipeline_data = {
        'git_repository': pipeline.git_repository,
        'registry': pipeline.registry,
        'output_type': pipeline.output_type,
        'branch': pipeline.branch,
        'image_tag': f"{pipeline.image_tag}-retry",
        'branding_template_id': pipeline.branding_template_id,
        'build_arguments': pipeline.build_arguments,
        'environment_variables': pipeline.environment_variables,
        'steps_to_execute': pipeline.steps_to_execute,
        'metadata': pipeline.metadata.copy() if pipeline.metadata else {}
    }

    if 'retry_count' in new_pipeline_data['metadata']:
        new_pipeline_data['metadata']['retry_count'] += 1
    else:
        new_pipeline_data['metadata']['retry_count'] = 1

    new_pipeline = PipelineRun.objects.create(**new_pipeline_data)

    messages.success(request, f'Pipeline retry "{new_pipeline.name}" started successfully.')
    return redirect('pipelines:detail', pk=new_pipeline.pk)
