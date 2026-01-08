"""
Django REST Framework views for pipelines app.

This module provides API views for pipeline run management including
CRUD operations, execution control, and build output handling.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from apps.pipelines.models import PipelineRun, BuildOutput, PipelineStatus, OutputType, BuildStatus
from apps.pipelines.api.serializers import (
    PipelineRunSerializer, PipelineRunCreateSerializer, PipelineRunUpdateSerializer,
    BuildOutputSerializer, PipelineStatusSerializer, PipelineStatisticsSerializer
)


class PipelinePagination(PageNumberPagination):
    """Custom pagination for pipelines."""

    page_size = 25
    page_size_query_param = 'per_page'
    max_page_size = 100


class PipelineRunViewSet(viewsets.ModelViewSet):
    """
    ViewSet for pipeline run management.

    Provides CRUD operations for pipeline runs with execution control
    and monitoring capabilities.
    """

    queryset = PipelineRun.objects.all()
    pagination_class = PipelinePagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return PipelineRunCreateSerializer
        elif self.action == 'update':
            return PipelineRunUpdateSerializer
        elif self.action == 'partial_update':
            return PipelineRunUpdateSerializer
        return PipelineRunSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by repository
        repository_id = self.request.query_params.get('repository_id')
        if repository_id:
            queryset = queryset.filter(git_repository_id=repository_id)

        # Filter by registry
        registry_id = self.request.query_params.get('registry_id')
        if registry_id:
            queryset = queryset.filter(registry_id=registry_id)

        # Filter by output type
        output_type = self.request.query_params.get('output_type')
        if output_type:
            queryset = queryset.filter(output_type=output_type)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        return queryset

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a pipeline run."""
        pipeline_run = self.get_object()

        if pipeline_run.status != PipelineStatus.PENDING:
            return Response(
                {'error': f'Cannot start pipeline in {pipeline_run.get_status_display()} status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status to running
        pipeline_run.status = PipelineStatus.RUNNING
        pipeline_run.worker_id = f"worker-{pipeline_run.id}"
        pipeline_run.save()

        serializer = self.get_serializer(pipeline_run)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop a running pipeline run."""
        pipeline_run = self.get_object()

        if pipeline_run.status != PipelineStatus.RUNNING:
            return Response(
                {'error': f'Cannot stop pipeline in {pipeline_run.get_status_display()} status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status to cancelled
        pipeline_run.status = PipelineStatus.CANCELLED
        pipeline_run.save()

        serializer = self.get_serializer(pipeline_run)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed pipeline run."""
        pipeline_run = self.get_object()

        if pipeline_run.status != PipelineStatus.FAILED:
            return Response(
                {'error': f'Cannot retry pipeline in {pipeline_run.get_status_display()} status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create new pipeline run with same parameters
        new_pipeline_run = PipelineRun.objects.create(
            git_repository=pipeline_run.git_repository,
            registry=pipeline_run.registry,
            output_type=pipeline_run.output_type,
            branch=pipeline_run.branch,
            commit_hash=pipeline_run.commit_hash,
            image_tag=f"{pipeline_run.image_tag}-retry",
            branding_template_id=pipeline_run.branding_template_id,
            build_arguments=pipeline_run.build_arguments,
            environment_variables=pipeline_run.environment_variables,
            steps_to_execute=pipeline_run.steps_to_execute,
            metadata=pipeline_run.metadata
        )

        serializer = self.get_serializer(new_pipeline_run)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Get pipeline run logs."""
        pipeline_run = self.get_object()

        # Return logs with pagination if needed
        logs = pipeline_run.logs or ""
        return Response({
            'pipeline_id': pipeline_run.id,
            'logs': logs,
            'log_file': pipeline_run.log_file
        })

    @action(detail=False, methods=['get'])
    def statuses(self, request):
        """Get information about pipeline statuses."""
        from apps.pipelines.models import PipelineRun

        status_info = PipelineRun.get_status_info()
        serializer = PipelineStatusSerializer(status_info, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get pipeline statistics."""
        # Calculate statistics
        total_runs = PipelineRun.objects.count()
        successful_runs = PipelineRun.objects.filter(status=PipelineStatus.COMPLETED).count()
        failed_runs = PipelineRun.objects.filter(status=PipelineStatus.FAILED).count()
        running_runs = PipelineRun.objects.filter(status=PipelineStatus.RUNNING).count()

        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0

        # Calculate average duration for completed runs
        completed_runs = PipelineRun.objects.filter(status=PipelineStatus.COMPLETED)
        total_duration = 0
        count = 0
        for run in completed_runs:
            if run.created_at and run.updated_at:
                duration = run.updated_at - run.created_at
                total_duration += duration.total_seconds()
                count += 1

        average_duration = int(total_duration / count) if count > 0 else 0

        stats = {
            'total_runs': total_runs,
            'successful_runs': successful_runs,
            'failed_runs': failed_runs,
            'running_runs': running_runs,
            'success_rate': success_rate,
            'average_duration_seconds': average_duration
        }

        serializer = PipelineStatisticsSerializer(stats)
        return Response(serializer.data)


class BuildOutputViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for build output management.

    Provides read-only operations for build outputs with download capabilities.
    """

    queryset = BuildOutput.objects.all()
    serializer_class = BuildOutputSerializer
    pagination_class = PipelinePagination

    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()

        # Filter by pipeline run
        pipeline_id = self.request.query_params.get('pipeline_id')
        if pipeline_id:
            queryset = queryset.filter(pipeline_run_id=pipeline_id)

        # Filter by output type
        output_type = self.request.query_params.get('output_type')
        if output_type:
            queryset = queryset.filter(output_type=output_type)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download build output file."""
        build_output = self.get_object()

        if not build_output.file_path:
            return Response(
                {'error': 'No file available for download'},
                status=status.HTTP_404_NOT_FOUND
            )

        # This would implement actual file serving
        # For now, return file information
        return Response({
            'id': build_output.id,
            'file_path': build_output.file_path,
            'file_url': build_output.file_url,
            'file_size_bytes': build_output.file_size_bytes,
            'download_available': True
        })

    @action(detail=True, methods=['post'])
    def mark_expired(self, request, pk=None):
        """Mark build output as expired."""
        build_output = self.get_object()

        build_output.status = BuildStatus.EXPIRED
        build_output.save()

        serializer = self.get_serializer(build_output)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def cleanup_expired(self, request):
        """Clean up expired build outputs."""
        from datetime import timedelta

        expiry_date = timezone.now() - timedelta(days=30)  # Default 30 days
        expired_count = BuildOutput.objects.filter(
            expires_at__lt=timezone.now(),
            status=BuildStatus.AVAILABLE
        ).update(status=BuildStatus.EXPIRED)

        return Response({
            'message': f'Successfully marked {expired_count} build outputs as expired',
            'count': expired_count
        })