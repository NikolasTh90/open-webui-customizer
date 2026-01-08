"""
Django models for container registry management.

This module contains the ContainerRegistry model which handles configuration
and authentication for various container registries like Docker Hub,
AWS ECR, Quay.io, and generic registries.
"""

import re
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseNameModel, MetadataModel, TimestampedMetadataModel
from apps.credentials.models import Credential


class RegistryType(models.TextChoices):
    """Enumeration of supported container registry types."""
    
    DOCKER_HUB = 'docker_hub', _('Docker Hub')
    AWS_ECR = 'aws_ecr', _('Amazon ECR')
    QUAY_IO = 'quay_io', _('Quay.io')
    GITHUB_REGISTRY = 'github_registry', _('GitHub Container Registry')
    GITLAB_REGISTRY = 'gitlab_registry', _('GitLab Container Registry')
    AZURE_REGISTRY = 'azure_registry', _('Azure Container Registry')
    GOOGLE_REGISTRY = 'google_registry', _('Google Container Registry')
    GENERIC = 'generic', _('Generic Registry')


def get_default_base_image():
    """Get the default base image from settings."""
    return getattr(settings, 'DEFAULT_BASE_IMAGE', 'ghcr.io/open-webui/open-webui:main')


def get_default_target_image():
    """Get the default target image from settings."""
    return getattr(settings, 'DEFAULT_TARGET_IMAGE', 'custom-open-webui:latest')


class ContainerRegistry(BaseNameModel):
    """
    Configuration for container registries for storing and distributing custom Open WebUI builds.
    
    This model stores connection information and credentials for various container registries
    where custom Open WebUI Docker images can be pushed and distributed.
    
    Inherits from:
    - BaseNameModel: provides name, timestamps, active status
    """
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadata",
        help_text="Additional metadata stored as JSON"
    )
    registry_type = models.CharField(
        max_length=20,
        choices=RegistryType.choices,
        default=RegistryType.DOCKER_HUB,
        verbose_name="Registry Type",
        help_text="Type of container registry"
    )
    base_image = models.CharField(
        max_length=255,
        default=get_default_base_image,
        verbose_name="Base Image",
        help_text="Source image to customize (e.g., open-webui/open-webui:main)"
    )
    target_image = models.CharField(
        max_length=255,
        default=get_default_target_image,
        verbose_name="Target Image",
        help_text="Target image name for custom builds (e.g., myrepo/custom-open-webui:v1.0)"
    )
    registry_url = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Registry URL",
        help_text="Custom registry URL (for generic registries)"
    )
    # AWS-specific fields
    aws_account_id = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="AWS Account ID",
        help_text="AWS Account ID for ECR registries"
    )
    aws_region = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="AWS Region",
        help_text="AWS region for ECR registries"
    )
    repository_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Repository Name",
        help_text="Repository name in the registry"
    )
    # Authentication fields (stored in Credential model)
    credential = models.ForeignKey(
        Credential,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='container_registries',
        verbose_name="Credential",
        help_text="Credential for registry authentication"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Is Verified",
        help_text="Whether this registry has been successfully verified"
    )
    verification_message = models.TextField(
        blank=True,
        verbose_name="Verification Message",
        help_text="Details about the last verification attempt"
    )
    last_pushed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Pushed At",
        help_text="Timestamp of the last successful image push"
    )
    
    class Meta:
        verbose_name = "Container Registry"
        verbose_name_plural = "Container Registries"
        ordering = ['name', 'registry_type']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['registry_type']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['last_pushed_at']),
        ]
        unique_together = [
            ['name', 'registry_url']
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_registry_type_display()})"
    
    def clean(self):
        """Validate the registry configuration."""
        super().clean()
        
        # Validate registry-specific fields
        self._validate_registry_fields()
        
        # Validate image names
        self._validate_image_names()
        
        # Validate credential compatibility
        self._validate_credential_compatibility()
    
    def _validate_registry_fields(self):
        """Validate registry-specific fields and configuration."""
        if self.registry_type == RegistryType.AWS_ECR:
            if not self.aws_account_id:
                raise ValidationError("AWS Account ID is required for ECR registries")
            if not self.aws_region:
                raise ValidationError("AWS Region is required for ECR registries")
            if not re.match(r'^\d{12}$', self.aws_account_id):
                raise ValidationError("AWS Account ID must be a 12-digit number")
            if not self.repository_name:
                raise ValidationError("Repository name is required for ECR registries")
        
        elif self.registry_type == RegistryType.GENERIC:
            if not self.registry_url:
                raise ValidationError("Registry URL is required for generic registries")
            
            # Validate URL format
            url_pattern = re.compile(
                r'^(?:https?://)?(?:[\w-]+\.)*[\w-]+[\w.-]*:[0-9]{1,5}$'
            )
            if ':' in self.registry_url and not url_pattern.match(self.registry_url):
                raise ValidationError("Registry URL format is invalid. Use: registry.example.com:5000")
        
        elif self.registry_type == RegistryType.DOCKER_HUB:
            if self.registry_url:
                raise ValidationError("Registry URL should not be set for Docker Hub")
            
            # Docker Hub repositories must be in format: owner/repo
            if '/' not in self.target_image:
                raise ValidationError(
                    "Target image for Docker Hub must include repository name "
                    "(e.g., username/custom-open-webui:latest)"
                )
        
        # Validate repository name formats
        if self.repository_name:
            # Docker image name validation
            if not re.match(r'^[a-z0-9]+(?:[._-][a-z0-9]+)*$', self.repository_name):
                raise ValidationError(
                    "Repository name contains invalid characters. "
                    "Use lowercase letters, numbers, dots, hyphens, and underscores."
                )
    
    def _validate_image_names(self):
        """Validate base and target image names."""
        # Docker image name validation pattern
        image_pattern = re.compile(
            r'^(?:[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*|'
            r'(?:[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*(?:\.[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*)*/)?'
            r'[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*(?:\.[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*)*)'
            r'(?::[a-zA-Z0-9][a-zA-Z0-9._-]*)?$'
        )
        
        if self.base_image and not image_pattern.match(self.base_image):
            raise ValidationError("Base image name format is invalid")
        
        if self.target_image and not image_pattern.match(self.target_image):
            raise ValidationError("Target image name format is invalid")
    
    def _validate_credential_compatibility(self):
        """Validate that the credential type is compatible with registry type."""
        if not self.credential:
            return
        
        from apps.credentials.models import CredentialType
        
        allowed_types = {
            RegistryType.DOCKER_HUB: [CredentialType.DOCKER_HUB],
            RegistryType.AWS_ECR: [CredentialType.AWS_ECR],
            RegistryType.QUAY_IO: [CredentialType.QUAY_IO],
            RegistryType.GITHUB_REGISTRY: [CredentialType.GIT_USERNAME_PASSWORD],
            RegistryType.GITLAB_REGISTRY: [CredentialType.GIT_USERNAME_PASSWORD],
            RegistryType.AZURE_REGISTRY: [CredentialType.GIT_USERNAME_PASSWORD],
            RegistryType.GOOGLE_REGISTRY: [CredentialType.GIT_USERNAME_PASSWORD],
            RegistryType.GENERIC: [CredentialType.GENERIC_REGISTRY],
        }
        
        valid_types = allowed_types.get(self.registry_type, [])
        
        if self.credential.credential_type not in valid_types:
            raise ValidationError(
                f"Credential type '{self.credential.get_credential_type_display()}' "
                f"is not compatible with {self.get_registry_type_display()} registries"
            )
    
    def save(self, *args, **kwargs):
        """Override save to handle registry validation."""
        is_new = self.pk is None
        
        # Clear verification message if registry configuration changed
        if not is_new:
            try:
                old_instance = ContainerRegistry.objects.get(pk=self.pk)
                changed_fields = []
                
                if old_instance.registry_type != self.registry_type:
                    changed_fields.append('registry_type')
                if old_instance.registry_url != self.registry_url:
                    changed_fields.append('registry_url')
                if old_instance.credential_id != self.credential_id:
                    changed_fields.append('credential')
                
                if changed_fields:
                    self.is_verified = False
                    self.verification_message = f"Registry configuration changed ({', '.join(changed_fields)}), re-verification required"
                    
            except ContainerRegistry.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
    
    def get_registry_url_for_docker(self):
        """
        Get the registry URL in the format Docker expects.
        
        Returns:
            str: Registry URL for Docker commands
        """
        if self.registry_type == RegistryType.DOCKER_HUB:
            return 'docker.io'
        elif self.registry_type == RegistryType.AWS_ECR:
            return f"{self.aws_account_id}.dkr.ecr.{self.aws_region}.amazonaws.com"
        elif self.registry_type == RegistryType.QUAY_IO:
            return 'quay.io'
        elif self.registry_type == RegistryType.GITHUB_REGISTRY:
            return 'ghcr.io'
        elif self.registry_type == RegistryType.GITLAB_REGISTRY:
            return 'registry.gitlab.com'
        elif self.registry_type == RegistryType.AZURE_REGISTRY:
            return f"{self.registry_url}"  # Already in correct format
        elif self.registry_type == RegistryType.GOOGLE_REGISTRY:
            return 'gcr.io'
        elif self.registry_type == RegistryType.GENERIC:
            return self.registry_url
        
        return ''
    
    def get_full_target_image(self, tag=None):
        """
        Get the full target image path including registry.
        
        Args:
            tag (str): Custom tag (uses target image tag if None)
            
        Returns:
            str: Full image path
        """
        registry_url = self.get_registry_url_for_docker()
        image_name = self.target_image
        
        # Replace tag if provided
        if tag and ':' in image_name:
            image_name = image_name.rsplit(':', 1)[0] + ':' + tag
        elif tag:
            image_name += ':' + tag
        
        if self.registry_type == RegistryType.DOCKER_HUB:
            return image_name  # Docker handle's registry automatically
        else:
            return f"{registry_url}/{image_name}"
    
    def get_docker_login_command(self):
        """
        Get the Docker login command for this registry.
        
        Returns:
            str: Docker login command or None if no credential
        """
        if not self.credential:
            return None
        
        registry_url = self.get_registry_url_for_docker()
        
        if self.registry_type == RegistryType.DOCKER_HUB:
            return f"docker login docker.io"
        elif self.registry_type == RegistryType.AWS_ECR:
            # ECR uses AWS CLI for login
            return f"aws ecr get-login-password --region {self.aws_region} | docker login --username AWS --password-stdin {registry_url}"
        else:
            return f"docker login {registry_url}"
    
    def verify_registry(self, force=False):
        """
        Verify that the registry is accessible and credentials are valid.
        
        Args:
            force (bool): Force verification even if recently verified
            
        Returns:
            dict: Verification result with success status and message
        """
        from apps.registries.services import RegistryVerificationService
        
        verification_service = RegistryVerificationService()
        result = verification_service.verify_registry(self, force=force)
        
        # Update verification status
        self.is_verified = result['success']
        self.verification_message = result['message']
        self.save(update_fields=['is_verified', 'verification_message'])
        
        return result
    
    def test_push(self, test_image='hello-world'):
        """
        Test pushing an image to the registry.
        
        Args:
            test_image (str): Small test image to push
            
        Returns:
            dict: Push test result
        """
        from apps.registries.services import RegistryPushService
        
        push_service = RegistryPushService()
        return push_service.test_push(self, test_image=test_image)
    
    def get_ecr_client(self):
        """
        Get an authenticated ECR client (for ECR registries).
        
        Returns:
            boto3.client: ECR client or None if not ECR
        """
        if self.registry_type != RegistryType.AWS_ECR:
            return None
        
        if not self.credential:
            return None
        
        try:
            credential_data = self.credential.get_credential_data()
            
            client = boto3.client(
                'ecr',
                region_name=self.aws_region,
                aws_access_key_id=credential_data.get('access_key_id'),
                aws_secret_access_key=credential_data.get('secret_access_key')
            )
            
            return client
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create ECR client: {str(e)}")
            return None
    
    def create_ecr_repository(self):
        """
        Create the ECR repository if it doesn't exist (for ECR registries).
        
        Returns:
            dict: Creation result
        """
        if self.registry_type != RegistryType.AWS_ECR:
            return {
                'success': False,
                'message': 'Not an ECR registry'
            }
        
        client = self.get_ecr_client()
        if not client:
            return {
                'success': False,
                'message': 'Failed to create ECR client'
            }
        
        try:
            try:
                # Check if repository exists
                client.describe_repositories(repositoryNames=[self.repository_name])
                return {
                    'success': True,
                    'message': 'Repository already exists'
                }
            except client.exceptions.RepositoryNotFoundException:
                # Create the repository
                response = client.create_repository(repositoryName=self.repository_name)
                
                return {
                    'success': True,
                    'message': f"Repository created: {response['repository']['repositoryUri']}",
                    'repository_uri': response['repository']['repositoryUri']
                }
                
        except ClientError as e:
            return {
                'success': False,
                'message': f"AWS error: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Unexpected error: {str(e)}"
            }
    
    def record_push(self):
        """Record that an image was successfully pushed to this registry."""
        self.last_pushed_at = timezone.now()
        self.save(update_fields=['last_pushed_at'])
    
    @property
    def requires_authentication(self):
        """Check if this registry requires authentication for pushes."""
        # Most registries require authentication except for public pulls
        return self.credential is not None
    
    @property
    def is_aws_registry(self):
        """Check if this is an AWS registry."""
        return self.registry_type == RegistryType.AWS_ECR
    
    @classmethod
    def get_verified_registries(cls):
        """Get all verified registries."""
        return cls.objects.filter(is_verified=True)
    
    @classmethod
    def get_registries_by_type(cls, registry_type):
        """Get registries of a specific type."""
        return cls.objects.filter(registry_type=registry_type)


# Signal receivers
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=ContainerRegistry)
def registry_saved(sender, instance, created, **kwargs):
    """Handle post-save actions for ContainerRegistry."""
    if created:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Container registry '{instance.name}' of type '{instance.registry_type}' created")
