"""
Service for Git operations including clone, fetch, and verification.

This service handles Git operations for custom fork cloning with support
for both HTTPS and SSH protocols with credential handling.

Author: Open WebUI Customizer Team
"""

import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from app.models.models import GitRepository
from app.services.credential_service import CredentialService
from app.config.settings import get_settings
from app.exceptions import (
    PipelineError, ValidationError, NotFoundError,
    FileOperationError
)
from app.utils.logging import get_logger, log_function_call

logger = get_logger(__name__)


class GitService:
    """
    Handles Git operations for custom fork cloning.
    
    Supports both HTTPS and SSH protocols with secure credential handling.
    All SSH keys are written to temporary files with restricted permissions
    and cleaned up immediately after use.
    
    Example:
        >>> service = GitService(db)
        >>> is_valid, repo_type, url = service.validate_repository_url("git@github.com:user/repo.git")
        >>> success, message = service.clone_repository(repo, "target_dir")
    """
    
    # Official repository URL for reference
    OFFICIAL_REPO_URL = "https://github.com/open-webui/open-webui.git"
    
    # SSH patterns
    SSH_PATTERNS = [
        r'^git@[\w\.-]+:[\w\.\-\/]+\.git$',
        r'^ssh://git@[\w\.-]+[\w\.\-\/]*\.git$'
    ]
    
    # HTTPS patterns
    HTTPS_PATTERNS = [
        r'^https?://[\w\.\-]+/[\w\.\-\/]+\.git$',
        r'^https?://[\w\.\-]+/[\w\.\-\/]*$'  # May not end with .git
    ]
    
    def __init__(self, db: Session):
        """
        Initialize the Git service.
        
        Args:
            db: Database session for persistence operations
        """
        self.db = db
        self.credential_service = CredentialService(db)
        
        # Track temporary files for cleanup
        self._temp_files: Dict[str, Path] = {}
        
        logger.info("Git service initialized")
    
    @log_function_call
    def validate_repository_url(self, url: str) -> Tuple[bool, str | None, str]:
        """
        Validate and parse a repository URL.
        
        Supports both SSH and HTTPS URLs for Git repositories.
        Host validation depends on environment settings.
        
        Args:
            url: Repository URL to validate
            
        Returns:
            Tuple of (is_valid, repo_type, normalized_url)
            
            - is_valid: True if URL format is valid
            - repo_type: 'ssh' or 'https' if valid
            - normalized_url: Normalized URL or error message
        """
        url = url.strip()
        
        if not url:
            return False, None, "Empty repository URL"
        
        # Check SSH patterns
        for pattern in self.SSH_PATTERNS:
            if re.match(pattern, url):
                # Validate host based on settings
                if self._validate_git_host(url, 'ssh'):
                    return True, 'ssh', url
                else:
                    return False, None, f"Git host not allowed for SSH URL: {url}"
        
        # Check HTTPS patterns
        for pattern in self.HTTPS_PATTERNS:
            if re.match(pattern, url):
                # Validate host based on settings
                if self._validate_git_host(url, 'https'):
                    # Normalize by adding .git if missing
                    if not url.endswith('.git'):
                        # Try to determine if it's a repo URL without .git
                        if '/tree/' not in url and '/blob/' not in url:
                            url = url.rstrip('/') + '.git'
                    return True, 'https', url
                else:
                    return False, None, f"Git host not allowed for HTTPS URL: {url}"
        
        return False, None, f"Invalid repository URL format: {url}"
    
    def _validate_git_host(self, url: str, repo_type: str) -> bool:
        """
        Validate that the Git host is allowed based on environment settings.
        
        Args:
            url: Repository URL
            repo_type: 'ssh' or 'https'
            
        Returns:
            True if host is allowed, False otherwise
        """
        settings = get_settings()
        
        # If any host is allowed, skip validation
        if getattr(settings.git, 'allow_any_git_host', False):
            return True
        
        # Get allowed hosts list
        allowed_hosts = getattr(settings.git, 'allowed_git_hosts', [])
        
        if not allowed_hosts:
            return True  # No restriction if list is empty
        
        # Extract host from URL
        if repo_type == 'https':
            parsed = urlparse(url)
            host = parsed.netloc
        elif repo_type == 'ssh':
            # Parse SSH URL: git@host:owner/repo.git
            url_parts = url.split(':')
            if len(url_parts) >= 2:
                host_part = url_parts[0].replace('git@', '')
                host = host_part
            else:
                return False
        else:
            return False
        
        # Check if host is in allowed list
        return host in allowed_hosts
    
    @log_function_call
    def clone_repository(
        self,
        repository: GitRepository,
        target_dir: str,
        branch: Optional[str] = None,
        depth: int = 1
    ) -> Tuple[bool, str]:
        """
        Clone a repository to the target directory.
        
        Args:
            repository: GitRepository model instance
            target_dir: Directory to clone into
            branch: Optional branch to clone (uses default from repo)
            depth: Git clone depth (1 for shallow clone)
            
        Returns:
            Tuple of (success, message)
            
        Raises:
            ValidationError: If repository is invalid
            PipelineError: If clone operation fails
            FileOperationError: If file operations fail
        """
        branch = branch or repository.default_branch
        
        try:
            # Validate target directory
            target_path = Path(target_dir)
            if target_path.exists() and any(target_path.iterdir()):
                raise FileOperationError(
                    "Target directory is not empty",
                    file_path=target_dir,
                    operation="clone"
                )
            
            # Prepare environment for credentials
            env = os.environ.copy()
            
            if repository.credential_id:
                try:
                    cred_data = self.credential_service.get_decrypted_credential(
                        repository.credential_id
                    )
                    env = self._setup_credential_environment(
                        repository.repository_type,
                        cred_data,
                        env
                    )
                except Exception as e:
                    logger.error(f"Failed to setup credentials: {str(e)}")
                    return False, f"Credential setup failed: {str(e)}"
            
            # Ensure target directory exists
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Build clone command
            cmd = ['git', 'clone']
            
            # Add depth for faster cloning
            if depth > 0:
                cmd.extend(['--depth', str(depth)])
            
            # Add branch specification
            cmd.extend(['--branch', branch])
            
            # Add repository URL and target
            cmd.extend([repository.repository_url, target_dir])
            
            logger.info(f"Cloning repository", extra={
                'repository_id': repository.id,
                'repository_name': repository.name,
                'repository_url': repository.repository_url,
                'target_dir': target_dir,
                'branch': branch,
                'depth': depth
            })
            
            # Execute clone
            result = subprocess.run(
                cmd,
                env=env,
                cwd=target_path.parent,
                capture_output=True,
                text=True,
                timeout=get_settings().git.git_timeout
            )
            
            # Clean up temporary credential files
            self._cleanup_temp_credentials()
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"Git clone failed", extra={
                    'repository_id': repository.id,
                    'exit_code': result.returncode,
                    'stderr': error_msg
                })
                
                # Clean up partial clone
                if target_path.exists():
                    shutil.rmtree(target_path, ignore_errors=True)
                
                return False, f"Clone failed: {error_msg}"
            
            # Verify clone was successful
            git_dir = target_path / '.git'
            if not git_dir.exists():
                return False, "Clone appears to have failed (.git directory not found)"
            
            # Get commit info for logging
            try:
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=target_path,
                    capture_output=True,
                    text=True
                )
                commit_hash = result.stdout.strip() if result.returncode == 0 else 'unknown'
                
                logger.info(f"Successfully cloned repository", extra={
                    'repository_id': repository.id,
                    'target_dir': target_dir,
                    'branch': branch,
                    'commit_hash': commit_hash
                })
                
                message = f"Successfully cloned {repository.name} ({branch} @ {commit_hash[:8]})"
                return True, message
                
            except Exception as e:
                logger.error(f"Failed to get clone details: {str(e)}")
                return True, f"Successfully cloned {repository.name} (details unavailable)"
            
        except subprocess.TimeoutExpired:
            self._cleanup_temp_credentials()
            
            # Clean up on timeout
            if Path(target_dir).exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            
            error_msg = "Clone operation timed out (5 minutes)"
            logger.error(f"Git clone timed out", extra={
                'repository_id': repository.id,
                'timeout_seconds': 300
            })
            
            return False, error_msg
            
        except (ValidationError, FileOperationError):
            self._cleanup_temp_credentials()
            raise
        except Exception as e:
            self._cleanup_temp_credentials()
            
            # Clean up on error
            if Path(target_dir).exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            
            logger.error(f"Unexpected error during clone: {str(e)}", extra={
                'repository_id': repository.id,
                'error_type': type(e).__name__
            })
            
            return False, f"Clone error: {str(e)}"
    
    def _setup_credential_environment(
        self,
        repo_type: str,
        cred_data: Dict[str, Any],
        env: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Set up environment variables for Git authentication.
        
        Configures SSH or HTTPS authentication based on credential type.
        SSH keys are written to temporary files with restricted permissions.
        
        Args:
            repo_type: Type of repository ('ssh' or 'https')
            cred_data: Decrypted credential data
            env: Environment variables to modify
            
        Returns:
            Modified environment dictionary
        """
        if repo_type == 'ssh':
            private_key = cred_data.get('private_key', '')
            if not private_key:
                raise ValidationError("SSH private key is required")
            
            # Create temporary SSH key file
            ssh_key_path = self._write_temp_ssh_key(private_key)
            
            # Configure SSH command
            ssh_cmd = f'ssh -i {ssh_key_path} -o StrictHostKeyChecking=no'
            
            # Add known hosts if provided
            if 'known_hosts' in cred_data:
                known_hosts_path = self._write_temp_known_hosts(cred_data['known_hosts'])
                ssh_cmd += f' -o UserKnownHostsFile={known_hosts_path}'
            else:
                # Disable known hosts verification (not recommended for production)
                ssh_cmd += ' -o UserKnownHostsFile=/dev/null -o GlobalKnownHostsFile=/dev/null'
            
            env['GIT_SSH_COMMAND'] = ssh_cmd
            
        elif repo_type == 'https':
            # Use credential helper for HTTPS
            username = cred_data.get('username', '')
            token = cred_data.get('password_or_token', '')
            
            if not username or not token:
                raise ValidationError("Username and token are required for HTTPS")
            
            # Create credential helper script
            helper_script = self._create_askpass_script(username, token)
            env['GIT_ASKPASS'] = helper_script
            env['GIT_USERNAME'] = username
            
        else:
            raise ValidationError(f"Unsupported repository type: {repo_type}")
        
        return env
    
    def _write_temp_ssh_key(self, private_key: str) -> str:
        """
        Write SSH private key to a temporary file with restricted permissions.
        
        Args:
            private_key: SSH private key content
            
        Returns:
            Path to temporary SSH key file
        """
        # Create temporary file
        fd, path = tempfile.mkstemp(suffix='_key', prefix='git_ssh_')
        
        try:
            # Write key with restricted permissions
            os.chmod(path, 0o600)
            
            with os.fdopen(fd, 'w') as f:
                f.write(private_key.strip() + '\n')
            
            # Track for cleanup
            self._temp_files['ssh_key'] = Path(path)
            
            logger.debug(f"Created temporary SSH key file", extra={
                'path': path,
                'size_bytes': os.path.getsize(path)
            })
            
            return path
            
        except Exception as e:
            # Ensure cleanup on error
            os.unlink(path)
            raise FileOperationError(
                f"Failed to write SSH key: {str(e)}",
                file_path=path,
                operation="write"
            )
    
    def _write_temp_known_hosts(self, known_hosts: str) -> str:
        """
        Write SSH known hosts to a temporary file.
        
        Args:
            known_hosts: Known hosts content
            
        Returns:
            Path to temporary known hosts file
        """
        fd, path = tempfile.mkstemp(suffix='_hosts', prefix='git_known_')
        
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(known_hosts.strip() + '\n')
            
            # Track for cleanup
            self._temp_files['known_hosts'] = Path(path)
            
            return path
            
        except Exception as e:
            os.unlink(path)
            raise FileOperationError(
                f"Failed to write known hosts: {str(e)}",
                file_path=path,
                operation="write"
            )
    
    def _create_askpass_script(self, username: str, token: str) -> str:
        """
        Create a GIT_ASKPASS script for HTTPS authentication.
        
        Args:
            username: Username for authentication
            token: Password or token for authentication
            
        Returns:
            Path to the helper script
        """
        script_content = f'#!/bin/bash\necho "{token}"'
        
        # Create temporary script
        fd, path = tempfile.mkstemp(suffix='.sh', prefix='git_askpass_')
        
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(script_content)
            
            # Make executable
            os.chmod(path, 0o700)
            
            # Track for cleanup
            self._temp_files['askpass_script'] = Path(path)
            
            return path
            
        except Exception as e:
            os.unlink(path)
            raise FileOperationError(
                f"Failed to create askpass script: {str(e)}",
                file_path=path,
                operation="write"
            )
    
    def _cleanup_temp_credentials(self) -> None:
        """Clean up all temporary credential files."""
        for name, path in self._temp_files.items():
            try:
                if path.exists():
                    path.unlink()
                    logger.debug(f"Cleaned up temporary file", extra={
                        'file': name,
                        'path': str(path)
                    })
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file", extra={
                    'file': name,
                    'path': str(path),
                    'error': str(e)
                })
        
        self._temp_files.clear()
    
    @log_function_call
    def verify_repository(self, repository_id: int) -> Tuple[bool, str]:
        """
        Verify that a repository can be accessed with current credentials.
        
        Uses 'git ls-remote' to check access without full clone.
        This is faster than cloning and verifies authentication works.
        
        Args:
            repository_id: ID of the repository to verify
            
        Returns:
            Tuple of (is_verified, verification_message)
            
        Raises:
            NotFoundError: If repository doesn't exist
            DatabaseError: If database operation fails
        """
        try:
            repository = self.db.query(GitRepository).filter(
                GitRepository.id == repository_id
            ).first()
            
            if not repository:
                raise NotFoundError(
                    f"Git repository with ID {repository_id} not found",
                    details={'repository_id': repository_id}
                )
            
            # Prepare environment
            env = os.environ.copy()
            
            if repository.credential_id:
                try:
                    cred_data = self.credential_service.get_decrypted_credential(
                        repository.credential_id
                    )
                    env = self._setup_credential_environment(
                        repository.repository_type,
                        cred_data,
                        env
                    )
                except Exception as e:
                    logger.error(f"Failed to setup credentials for verification: {str(e)}")
                    
                    # Update repository status
                    repository.is_verified = False
                    repository.verification_status = 'failed'
                    repository.verification_message = f"Credential error: {str(e)}"
                    self.db.commit()
                    
                    return False, repository.verification_message
            
            # Test with ls-remote
            cmd = ['git', 'ls-remote', '--heads', repository.repository_url]
            
            logger.info(f"Verifying repository access", extra={
                'repository_id': repository.id,
                'repository_name': repository.name,
                'repository_url': repository.repository_url
            })
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=get_settings().git.git_timeout // 5  # Use 1/5 of clone timeout for verification
            )
            
            # Clean up temporary files
            self._cleanup_temp_credentials()
            
            # Update repository verification status
            if result.returncode == 0:
                repository.is_verified = True
                repository.verification_status = 'success'
                
                # Count available branches
                if result.stdout:
                    branch_count = len(result.stdout.strip().split('\n'))
                    repository.verification_message = f"Verified - {branch_count} branches accessible"
                else:
                    repository.verification_message = "Verified - repository accessible"
                
                logger.info(f"Repository verification successful", extra={
                    'repository_id': repository.id,
                    'message': repository.verification_message
                })
            else:
                repository.is_verified = False
                repository.verification_status = 'failed'
                repository.verification_message = f"Access denied: {result.stderr}"
                
                logger.error(f"Repository verification failed", extra={
                    'repository_id': repository.id,
                    'error': result.stderr
                })
            
            repository.updated_at = datetime.utcnow()
            self.db.commit()
            
            return repository.is_verified, repository.verification_message
            
        except subprocess.TimeoutExpired:
            self._cleanup_temp_credentials()
            
            repository.is_verified = False
            repository.verification_status = 'failed'
            repository.verification_message = 'Verification timeout'
            repository.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.error(f"Repository verification timed out", extra={
                'repository_id': repository_id
            })
            
            return False, 'Verification timed out'
            
        except (NotFoundError, ValidationError):
            self._cleanup_temp_credentials()
            raise
        except Exception as e:
            self._cleanup_temp_credentials()
            
            repository.is_verified = False
            repository.verification_status = 'failed'
            repository.verification_message = f"Unexpected error: {str(e)}"
            repository.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.error(f"Repository verification error: {str(e)}", extra={
                'repository_id': repository_id,
                'error_type': type(e).__name__
            })
            
            return False, f"Verification error: {str(e)}"
    
    @log_function_call
    def get_repository_info(self, repository_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a repository.
        
        Retrieves metadata including branch information, last commit,
        and other useful details without cloning.
        
        Args:
            repository_id: ID of the repository
            
        Returns:
            Dictionary with repository information
            
        Raises:
            NotFoundError: If repository doesn't exist
            ValidationError: If verification fails
        """
        try:
            repository = self.db.query(GitRepository).filter(
                GitRepository.id == repository_id
            ).first()
            
            if not repository:
                raise NotFoundError(
                    f"Git repository with ID {repository_id} not found",
                    details={'repository_id': repository_id}
                )
            
            info = {
                'id': repository.id,
                'name': repository.name,
                'url': repository.repository_url,
                'type': repository.repository_type,
                'default_branch': repository.default_branch,
                'is_verified': repository.is_verified,
                'verification_status': repository.verification_status,
                'verification_message': repository.verification_message,
                'is_experimental': repository.is_experimental,
                'created_at': repository.created_at.isoformat(),
                'updated_at': repository.updated_at.isoformat()
            }
            
            # Parse repository URL for additional info
            parsed = urlparse(repository.repository_url)
            
            if repository.repository_type == 'https':
                info['host'] = parsed.netloc
                info['owner'] = parsed.path.split('/')[1] if len(parsed.path.split('/')) > 1 else 'unknown'
                info['repo_name'] = parsed.path.split('/')[-1].replace('.git', '')
            elif repository.repository_type == 'ssh':
                # Parse SSH URL: git@host:owner/repo.git
                url_parts = repository.repository_url.split(':')
                if len(url_parts) >= 2:
                    host_part = url_parts[0].replace('git@', '')
                    repo_part = url_parts[1].replace('.git', '')
                    path_parts = repo_part.split('/')
                    
                    info['host'] = host_part
                    info['owner'] = path_parts[0] if len(path_parts) > 1 else 'unknown'
                    info['repo_name'] = path_parts[-1] if len(path_parts) > 0 else 'unknown'
            
            return info
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting repository info: {str(e)}", extra={
                'repository_id': repository_id
            })
            raise ValidationError(f"Failed to get repository info: {str(e)}")
    
    def __del__(self):
        """Cleanup when service is destroyed."""
        try:
            self._cleanup_temp_credentials()
        except:
            pass  # Ignore errors during cleanup