"""
Django REST Framework serializers for pipelines app.

This module provides serializers for converting PipelineRun and BuildOutput models
and related data to/from JSON representations for the API.
"""

from rest_framework import serializers
from apps.pipelines.models import PipelineRun, BuildOutput, PipelineStatus, OutputType, BuildStatus


class BuildOutputSerializer(serializers.ModelSerializer):
    """
    Serializer for BuildOutput model.

    Handles serialization of build outputs with file information and status.
    """

    output_type_display = serializers.CharField(
        source='get_output_type_display',
        read_only=True
    )

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    is_expired = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = BuildOutput
        fields = [
            'id', 'output_type', 'output_type_display', 'status',
            'status_display', 'file_path', 'file_url', 'image_url',
            'file_size_bytes', 'checksum_sha256', 'expires_at',
            'is_expired', 'download_url', 'build_metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_expired(self, obj):
        """Check if build output has expired."""
        return obj.is_expired if hasattr(obj, 'is_expired') else False

    def get_download_url(self, obj):
        """Get download URL for the build output."""
        if obj.file_url:
            return obj.file_url
        # Generate download URL based on file_path
        return f"/api/v1/pipelines/outputs/{obj.id}/download/"


class PipelineRunSerializer(serializers.ModelSerializer):
    """
    Serializer for PipelineRun model.

    Handles serialization of pipeline runs with status, progress, and outputs.
    """

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    output_type_display = serializers.CharField(
        source='get_output_type_display',
        read_only=True
    )

    progress_percentage = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    outputs = BuildOutputSerializer(many=True, read_only=True, source='buildoutput_set')

    class Meta:
        model = PipelineRun
        fields = [
            'id', 'status', 'status_display', 'output_type',
            'output_type_display', 'git_repository', 'registry',
            'steps_to_execute', 'worker_id', 'progress_percentage',
            'current_step', 'branch', 'commit_hash', 'image_tag',
            'branding_template_id', 'build_arguments', 'environment_variables',
            'error_message', 'logs', 'log_file', 'duration_seconds',
            'outputs', 'created_at', 'updated_at', 'metadata'
        ]
        read_only_fields = [
            'id', 'worker_id', 'progress_percentage', 'current_step',
            'created_at', 'updated_at', 'duration_seconds'
        ]

    def get_progress_percentage(self, obj):
        """Calculate progress percentage based on status."""
        if obj.status == PipelineStatus.COMPLETED:
            return 100
        elif obj.status == PipelineStatus.FAILED:
            return 0
        elif obj.status == PipelineStatus.RUNNING:
            # This would be calculated based on current step
            return obj.progress_percentage or 50
        else:
            return 0

    def get_duration_seconds(self, obj):
        """Calculate pipeline duration in seconds."""
        if obj.created_at and obj.updated_at:
            duration = obj.updated_at - obj.created_at
            return int(duration.total_seconds())
        return None


class PipelineRunCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new pipeline runs.

    Includes validation for required fields and relationships.
    """

    class Meta:
        model = PipelineRun
        fields = [
            'git_repository', 'registry', 'output_type', 'branch',
            'image_tag', 'branding_template_id', 'build_arguments',
            'environment_variables', 'steps_to_execute', 'metadata'
        ]

    def validate_git_repository(self, value):
        """Validate that the Git repository exists and is active."""
        if not value.is_active:
            raise serializers.ValidationError("Git repository is not active")
        return value

    def validate_registry(self, value):
        """Validate that the registry exists and is active."""
        if not value.is_active:
            raise serializers.ValidationError("Container registry is not active")
        return value

    def validate_steps_to_execute(self, value):
        """Validate pipeline steps."""
        valid_steps = ['clone', 'build', 'brand', 'push', 'test']
        invalid_steps = [step for step in value if step not in valid_steps]
        if invalid_steps:
            raise serializers.ValidationError(
                f"Invalid steps: {', '.join(invalid_steps)}. Valid steps: {', '.join(valid_steps)}"
            )
        return value


class PipelineRunUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating pipeline runs.

    Limited fields can be updated during execution.
    """

    class Meta:
        model = PipelineRun
        fields = ['status', 'progress_percentage', 'current_step', 'error_message']
        read_only_fields = ['status']  # Status should be updated by the pipeline worker


class PipelineStatusSerializer(serializers.Serializer):
    """
    Serializer for pipeline status information.
    """

    status = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    is_final = serializers.BooleanField()
    color = serializers.CharField()


class PipelineStatisticsSerializer(serializers.Serializer):
    """
    Serializer for pipeline statistics.
    """

    total_runs = serializers.IntegerField()
    successful_runs = serializers.IntegerField()
    failed_runs = serializers.IntegerField()
    running_runs = serializers.IntegerField()
    success_rate = serializers.FloatField()
    average_duration_seconds = serializers.IntegerField()