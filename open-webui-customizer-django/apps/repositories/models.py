"""
Django models for Git repository management.

This module contains the GitRepository model which handles configuration
and management of Git repositories for building custom forks of Open WebUI.
Supports both HTTPS and SSH protocols with credential binding.
"""

import os
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseNameModel, MetadataModel, TimestampedMetadataModel
from apps.credentials.models import Credential


class RepositoryType(models.TextChoices):
    """Enumeration of supported repository types."""
    
    HTTPS = 'https', _('HTTPS')
    SSH = 'ssh', _('SSH')
    GIT = 'git', _('Git Protocol')


class VerificationStatus(models.TextChoices):
    """Enumeration of repository verification statuses."""
    
    PENDING = 'pending', _('Pending Verification')
    VERIFIED = 'verified', _('Verified')
    FAILED = 'failed', _('Verification Failed')
    DISABLED = 'disabled', _('Disabled')


class GitRepository(BaseNameModel):
    """
    Configured Git repository for building custom forks.
    
    This model stores configuration information about Git repositories
    that can be used as sources for custom Open WebUI builds. It supports
    both HTTPS and SSH protocols and can be associated with credentials
    for authentication.
    
    Inherits from:
    - BaseNameModel: provides name, timestamps, active status
    """
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadata",
        help_text="Additional metadata stored as JSON"
    )
    repository_url = models.URLField(
        max_length=1024,
        verbose_name="Repository URL",
        help_text="Full URL to the Git repository"
    )
    repository_type = models.CharField(
        max_length=20,
        choices=RepositoryType.choices,
        default=RepositoryType.HTTPS,
        verbose_name="Repository Type",
        help_text="Protocol type for accessing the repository"
    )
    default_branch = models.CharField(
        max_length=255,
        default='main',
        verbose_name="Default Branch",
        help_text="Default branch to use for builds"
    )
    credential = models.ForeignKey(
        Credential,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='git_repositories',
        verbose_name="Credential",
        help_text="Optional credential for repository access"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Is Verified",
        help_text="Whether this repository has been successfully verified"
    )
    verification_status = models.CharField(
        max_length=50,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        verbose_name="Verification Status",
        help_text="Current verification status"
    )
    verification_message = models.TextField(
        blank=True,
        verbose_name="Verification Message",
        help_text="Details about the last verification attempt"
    )
    is_experimental = models.BooleanField(
        default=True,
        verbose_name="Is Experimental",
        help_text="Experimental repositories are marked as such in the UI"
    )
    last_commit_hash = models.CharField(
        max_length=40,
        blank=True,
        verbose_name="Last Commit Hash",
        help_text="Hash of the last known commit"
    )
    last_commit_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Commit Date",
        help_text="Date of the last known commit"
    )
    clone_path = models.CharField(
        max_length=1024,
        blank=True,
        verbose_name="Clone Path",
        help_text="Local path where repository is cloned"
    )
    
    class Meta:
        verbose_name = "Git Repository"
        verbose_name_plural = "Git Repositories"
        ordering = ['name', 'repository_type']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['repository_type']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['is_experimental']),
            models.Index(fields=['last_commit_date']),
        ]
        unique_together = [
            ['name', 'repository_url']
        ]
    
    def __str__(self):
        return f"{self.name} ({self.repository_type})"
    
    def clean(self):
        """Validate the repository configuration."""
        super().clean()
        
        # Validate URL format matches repository type
        self._validate_url_format()
        
        # Validate credential compatibility with repository type
        self._validate_credential_compatibility()
        
        # Validate default branch name
        self._validate_default_branch()
    
    def _validate_url_format(self):
        """Validate that the URL format matches the repository type."""
        url = self.repository_url.lower()
        
        if self.repository_type == RepositoryType.HTTPS:
            if not (url.startswith('https://') or url.startswith('http://')):
                raise ValidationError("HTTPS repositories must use http:// or https:// URLs")
        elif self.repository_type == RepositoryType.SSH:
            if not url.startswith(('git@', 'ssh://')):
                raise ValidationError("SSH repositories must use git@ or ssh:// URLs")
        elif self.repository_type == RepositoryType.GIT:
            if not url.startswith('git://'):
                raise ValidationError("Git protocol repositories must use git:// URLs")
    
    def _validate_credential_compatibility(self):
        """Validate that the credential type is compatible with repository type."""
        if not self.credential:
            return
        
        from apps.credentials.models import CredentialType
        
        if self.repository_type == RepositoryType.HTTPS:
            allowed_types = [
                CredentialType.GIT_HTTPS_TOKEN,
                CredentialType.GIT_USERNAME_PASSWORD,
            ]
        elif self.repository_type == RepositoryType.SSH:
            allowed_types = [CredentialType.GIT_SSH_KEY]
        else:
            allowed_types = []
        
        if self.credential.credential_type not in allowed_types:
            raise ValidationError(
                f"Credential type '{self.credential.get_credential_type_display()}' "
                f"is not compatible with {self.repository_type} repositories"
            )
    
    def _validate_default_branch(self):
        """Validate the default branch name format."""
        if not self.default_branch:
            raise ValidationError("Default branch is required")
        
        # Git branch name validation
        if not re.match(r'^[a-zA-Z0-9/_-]+$', self.default_branch):
            raise ValidationError(
                "Default branch contains invalid characters. "
                "Only letters, numbers, hyphens, underscores, and forward slashes are allowed."
            )
    
    def save(self, *args, **kwargs):
        """Override save to handle repository validation."""
        is_new = self.pk is None
        
        # Set verification status to pending if URL changed
        if not is_new:
            try:
                old_instance = GitRepository.objects.get(pk=self.pk)
                if old_instance.repository_url != self.repository_url:
                    self.verification_status = VerificationStatus.PENDING
                    self.is_verified = False
                    self.verification_message = "Repository URL changed, re-verification required"
            except GitRepository.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
    
    def get_git_url(self):
        """
        Get the Git URL formatted for Git commands.
        
        Returns:
            str: Git-formatted URL
        """
        url = self.repository_url
        
        if self.repository_type == RepositoryType.HTTPS:
            return url
        elif self.repository_type == RepositoryType.SSH:
            # Convert git@host:owner/repo.git to ssh://git@host/owner/repo.git
            if url.startswith('git@'):
                return url.replace(':', '/', 1).replace('git@', 'ssh://git@', 1)
            return url
        elif self.repository_type == RepositoryType.GIT:
            return url
        
        return url
    
    def get_clone_directory(self):
        """
        Get the directory name for cloning this repository.
        
        Returns:
            str: Directory name for cloning
        """
        # Generate a safe directory name from the repository URL
        parsed = urlparse(self.repository_url)
        path = parsed.path.rstrip('/')
        
        # Extract repository name from path
        repo_name = path.split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        
        # Add unique identifier to avoid conflicts
        safe_name = f"{repo_name}_{self.pk}"
        return re.sub(r'[^\w\-_.]', '_', safe_name)
    
    def get_full_clone_path(self):
        """
        Get the full local path for cloning this repository.
        
        Returns:
            str: Full local clone path
        """
        clone_dir = self.get_clone_directory()
        base_path = getattr(settings, 'GIT_CLONE_BASE_PATH', '/tmp/git_repositories')
        return os.path.join(base_path, clone_dir)
    
    def verify_repository(self, force=False):
        """
        Verify that the repository is accessible and valid.
        
        Args:
            force (bool): Force verification even if recently verified
            
        Returns:
            dict: Verification result with success status and message
        """
        from apps.repositories.services import GitVerificationService
        
        verification_service = GitVerificationService()
        result = verification_service.verify_repository(self, force=force)
        
        # Update verification status
        self.is_verified = result['success']
        self.verification_status = (
            VerificationStatus.VERIFIED if result['success']
            else VerificationStatus.FAILED
        )
        self.verification_message = result['message']
        self.save(update_fields=[
            'is_verified', 'verification_status', 'verification_message'
        ])
        
        return result
    
    def test_clone(self, branch=None, depth=None):
        """
        Test cloning the repository to verify access.
        
        Args:
            branch (str): Branch to clone (uses default if None)
            depth (int): Clone depth for shallow clone
            
        Returns:
            dict: Clone test result
        """
        from apps.repositories.services import GitCloneService
        
        clone_service = GitCloneService()
        return clone_service.test_clone(self, branch=branch, depth=depth)
    
    def get_branches(self):
        """
        Get list of available branches in the repository.
        
        Returns:
            list: List of branch names
        """
        from apps.repositories.services import GitBranchService
        
        branch_service = GitBranchService()
        return branch_service.get_branches(self)
    
    def get_commits(self, branch=None, limit=20):
        """
        Get list of recent commits for a branch.
        
        Args:
            branch (str): Branch to get commits from (uses default if None)
            limit (int): Maximum number of commits to return
            
        Returns:
            list: List of commit dictionaries
        """
        from apps.repositories.services import GitCommitService
        
        commit_service = GitCommitService()
        return commit_service.get_commits(self, branch=branch, limit=limit)
    
    def update_commit_info(self):
        """
        Update the last commit hash and date information.
        
        Returns:
            bool: True if update was successful
        """
        try:
            commits = self.get_commits(limit=1)
            
            if commits:
                latest = commits[0]
                self.last_commit_hash = latest.get('hash', '')
                
                # Parse commit date
                commit_date_str = latest.get('date')
                if commit_date_str:
                    # Parse ISO 8601 date string
                    try:
                        import dateutil.parser
                        self.last_commit_date = dateutil.parser.parse(commit_date_str)
                    except Exception:
                        self.last_commit_date = timezone.now()
                else:
                    self.last_commit_date = timezone.now()
                
                self.save(update_fields=['last_commit_hash', 'last_commit_date'])
                return True
            
            return False
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to update commit info for repository {self.pk}: {str(e)}")
            return False
    
    def clone_repository(self, destination=None, branch=None):
        """
        Clone the repository to a local directory.
        
        Args:
            destination (str): Destination directory (auto-generated if None)
            branch (str): Branch to clone (uses default if None)
            
        Returns:
            dict: Clone result with success status and path
        """
        from apps.repositories.services import GitCloneService
        
        clone_service = GitCloneService()
        return clone_service.clone_repository(self, destination=destination, branch=branch)
    
    def cleanup_clone(self):
        """
        Clean up the cloned repository directory.
        
        Returns:
            bool: True if cleanup was successful
        """
        import shutil
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            clone_path = self.get_full_clone_path()
            
            if os.path.exists(clone_path):
                shutil.rmtree(clone_path)
                logger.info(f"Cleaned up clone directory: {clone_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cleanup clone directory for repository {self.pk}: {str(e)}")
            return False
    
    def get_web_url(self):
        """
        Get the web URL for the repository (for viewing in browser).
        
        Returns:
            str: Web URL or None if cannot be determined
        """
        url = self.repository_url
        
        if self.repository_type == RepositoryType.HTTPS:
            # HTTPS URL is already the web URL
            return url
        elif self.repository_type == RepositoryType.SSH:
            # Convert git@github.com:owner/repo.git to https://github.com/owner/repo
            if url.startswith('git@'):
                url = url.replace('git@', 'https://').replace(':', '/', 1)
            elif url.startswith('ssh://git@'):
                url = url.replace('ssh://git@', 'https://')
            return url.rsplit('.git', 1)[0]
        
        return None
    
    def get_repository_identifier(self):
        """
        Get a unique identifier for the repository (owner/name).
        
        Returns:
            str: Repository identifier (owner/name) or URL if cannot parse
        """
        url = self.repository_url
        parsed = urlparse(url)
        
        # Extract path and remove .git suffix if present
        path = parsed.path.rstrip('/')
        if path.endswith('.git'):
            path = path[:-4]
        
        # Remove leading slash
        if path.startswith('/'):
            path = path[1:]
        
        return path or url
    
    @classmethod
    def get_verified_repositories(cls):
        """Get all verified repositories."""
        return cls.objects.filter(
            is_verified=True,
            verification_status=VerificationStatus.VERIFIED
        )
    
    @classmethod
    def get_repositories_needing_verification(cls):
        """Get repositories that need verification."""
        return cls.objects.filter(
            models.Q(verification_status=VerificationStatus.PENDING) |
            models.Q(is_verified=False)
        )
    
    @property
    def can_be_used_for_builds(self):
        """Check if this repository can be used for builds."""
        return (
            self.is_active and 
            self.is_verified and 
            self.verification_status == VerificationStatus.VERIFIED
        )


# Signal receivers
from django.db.models.signals import pre_delete
from django.dispatch import receiver

@receiver(pre_delete, sender=GitRepository)
def repository_deleted(sender, instance, **kwargs):
    """Handle cleanup when a GitRepository is deleted."""
    # Clean up any cloned local files
    instance.cleanup_clone()
