"""
Service for managing Git repositories.

This service provides high-level operations for Git repository management
including CRUD operations, validation, and verification.

Author: Open WebUI Customizer Team
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import GitRepository, Credential
from app.services.git_service import GitService
from app.services.credential_service import CredentialService
from app.exceptions import (
    ValidationError, NotFoundError, DatabaseError,
    DuplicateResourceError
)
from app.utils.logging import get_logger, log_function_call

logger = get_logger(__name__)


class GitRepositoryService:
    """
    Service for managing Git repositories in the database.
    
    Provides CRUD operations, validation, and integration with Git operations.
    All database operations are logged and validated.
    
    Example:
        >>> service = GitRepositoryService(db)
        >>> repo = service.create_repository(name="My Fork", url="git@github.com:user/repo.git")
        >>> repositories = service.get_all_repositories()
    """
    
    def __init__(self, db: Session):
        """
        Initialize the Git repository service.
        
        Args:
            db: Database session for persistence operations
        """
        self.db = db
        self.git_service = GitService(db)
        self.credential_service = CredentialService(db)
        
        logger.info("Git repository service initialized")
    
    @log_function_call
    def create_repository(
        self,
        name: str,
        repository_url: str,
        credential_id: Optional[int] = None,
        default_branch: str = "main",
        is_experimental: bool = False,
        description: Optional[str] = None
    ) -> GitRepository:
        """
        Create a new Git repository.
        
        Args:
            name: Human-readable name for the repository
            repository_url: Git repository URL (SSH or HTTPS)
            credential_id: Optional credential ID for authentication
            default_branch: Default branch name (main or master)
            is_experimental: Whether this is an experimental repository
            description: Optional description
            
        Returns:
            Created GitRepository instance
            
        Raises:
            ValidationError: If input validation fails
            DuplicateResourceError: If repository URL already exists
            NotFoundError: If credential doesn't exist
            DatabaseError: If database operation fails
        """
        # Validate inputs
        if not name or not name.strip():
            raise ValidationError("Repository name is required")
        
        if not repository_url or not repository_url.strip():
            raise ValidationError("Repository URL is required")
        
        name = name.strip()
        repository_url = repository_url.strip()
        
        # Validate repository URL format
        is_valid, repo_type, normalized_url = self.git_service.validate_repository_url(repository_url)
        if not is_valid:
            raise ValidationError(f"Invalid repository URL: {normalized_url}")
        
        # Check for duplicate URL
        existing = self.db.query(GitRepository).filter(
            func.lower(GitRepository.repository_url) == func.lower(normalized_url)
        ).first()
        
        if existing:
            raise DuplicateResourceError(
                "Repository URL already exists",
                resource_type="repository",
                conflict_field="repository_url",
                existing_id=existing.id
            )
        
        # Validate credential if provided
        if credential_id:
            credential = self.db.query(Credential).filter(Credential.id == credential_id).first()
            if not credential:
                raise NotFoundError(
                    f"Credential with ID {credential_id} not found",
                    details={'credential_id': credential_id}
                )
        
        # Validate branch name
        valid_branch_names = ['main', 'master', 'develop']
        if default_branch not in valid_branch_names:
            raise ValidationError(f"Invalid default branch. Must be one of: {', '.join(valid_branch_names)}")
        
        # Create repository
        try:
            repository = GitRepository(
                name=name,
                repository_url=normalized_url,
                repository_type=repo_type,  # From validation
                default_branch=default_branch,
                credential_id=credential_id,
                is_experimental=is_experimental,
                description=description,
                is_verified=False,
                verification_status='pending',
                verification_message='Repository created, verification pending'
            )
            
            self.db.add(repository)
            self.db.commit()
            self.db.refresh(repository)
            
            logger.info(f"Created Git repository", extra={
                'repository_id': repository.id,
                'name': name,
                'repository_type': repo_type,
                'is_experimental': is_experimental
            })
            
            # Verify repository access
            try:
                is_verified, message = self.git_service.verify_repository(repository.id)
                logger.info(f"Repository verification result", extra={
                    'repository_id': repository.id,
                    'is_verified': is_verified,
                    'message': message
                })
            except Exception as e:
                logger.warning(f"Repository verification failed", extra={
                    'repository_id': repository.id,
                    'error': str(e)
                })
            
            return repository
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create Git repository: {str(e)}")
            raise DatabaseError(f"Failed to create repository: {str(e)}")
    
    @log_function_call
    def get_repository(self, repository_id: int) -> GitRepository:
        """
        Get a Git repository by ID.
        
        Args:
            repository_id: ID of the repository
            
        Returns:
            GitRepository instance
            
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
            
            return repository
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get Git repository: {str(e)}")
            raise DatabaseError(f"Failed to get repository: {str(e)}")
    
    @log_function_call
    def get_all_repositories(self, include_experimental: bool = False) -> List[GitRepository]:
        """
        Get all Git repositories.
        
        Args:
            include_experimental: Whether to include experimental repositories
            
        Returns:
            List of GitRepository instances
        """
        try:
            query = self.db.query(GitRepository)
            
            if not include_experimental:
                query = query.filter(GitRepository.is_experimental == False)
            
            repositories = query.order_by(GitRepository.created_at.desc()).all()
            
            logger.debug(f"Retrieved {len(repositories)} repositories", extra={
                'include_experimental': include_experimental
            })
            
            return repositories
            
        except Exception as e:
            logger.error(f"Failed to get repositories: {str(e)}")
            raise DatabaseError(f"Failed to get repositories: {str(e)}")
    
    @log_function_call
    def update_repository(
        self,
        repository_id: int,
        name: Optional[str] = None,
        credential_id: Optional[int] = None,
        default_branch: Optional[str] = None,
        is_experimental: Optional[bool] = None,
        description: Optional[str] = None
    ) -> GitRepository:
        """
        Update a Git repository.
        
        Args:
            repository_id: ID of the repository to update
            name: New name
            credential_id: New credential ID
            default_branch: New default branch
            is_experimental: New experimental flag
            description: New description
            
        Returns:
            Updated GitRepository instance
            
        Raises:
            NotFoundError: If repository doesn't exist
            ValidationError: If validation fails
            DatabaseError: If database operation fails
        """
        try:
            repository = self.get_repository(repository_id)
            
            # Validate credential if provided
            if credential_id is not None:
                if credential_id == 0:
                    repository.credential_id = None
                else:
                    credential = self.db.query(Credential).filter(Credential.id == credential_id).first()
                    if not credential:
                        raise NotFoundError(
                            f"Credential with ID {credential_id} not found",
                            details={'credential_id': credential_id}
                        )
                    repository.credential_id = credential_id
            
            # Validate branch name if provided
            if default_branch is not None:
                valid_branch_names = ['main', 'master', 'develop']
                if default_branch not in valid_branch_names:
                    raise ValidationError(f"Invalid default branch. Must be one of: {', '.join(valid_branch_names)}")
                repository.default_branch = default_branch
            
            # Update other fields
            if name is not None:
                if not name or not name.strip():
                    raise ValidationError("Repository name cannot be empty")
                repository.name = name.strip()
            
            if is_experimental is not None:
                repository.is_experimental = is_experimental
            
            if description is not None:
                repository.description = description.strip() if description else None
            
            repository.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(repository)
            
            logger.info(f"Updated Git repository", extra={
                'repository_id': repository.id,
                'name': repository.name
            })
            
            # Re-verify repository if credentials changed
            if credential_id is not None:
                try:
                    is_verified, message = self.git_service.verify_repository(repository.id)
                    logger.info(f"Repository verification after credential update", extra={
                        'repository_id': repository.id,
                        'is_verified': is_verified,
                        'message': message
                    })
                except Exception as e:
                    logger.warning(f"Repository verification failed after update", extra={
                        'repository_id': repository.id,
                        'error': str(e)
                    })
            
            return repository
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update Git repository: {str(e)}", extra={
                'repository_id': repository_id
            })
            raise DatabaseError(f"Failed to update repository: {str(e)}")
    
    @log_function_call
    def delete_repository(self, repository_id: int) -> Dict[str, Any]:
        """
        Delete a Git repository.
        
        Args:
            repository_id: ID of the repository to delete
            
        Returns:
            Dictionary with deletion status
            
        Raises:
            NotFoundError: If repository doesn't exist
            DatabaseError: If database operation fails
        """
        try:
            repository = self.get_repository(repository_id)
            
            # Store info for response
            repo_info = {
                'id': repository.id,
                'name': repository.name,
                'repository_url': repository.repository_url
            }
            
            # Check if repository is used in any pipelines
            from app.models.models import Pipeline  # Local import to avoid circular dependency
            pipeline_count = self.db.query(Pipeline).filter(
                Pipeline.git_repository_id == repository_id
            ).count()
            
            if pipeline_count > 0:
                logger.warning(f"Attempting to delete repository used by pipelines", extra={
                    'repository_id': repository_id,
                    'pipeline_count': pipeline_count
                })
                # In a real implementation, you might want to prevent deletion
                # or handle relationship cleanup properly
            
            self.db.delete(repository)
            self.db.commit()
            
            logger.info(f"Deleted Git repository", extra={
                'repository_id': repository_id,
                'name': repository.name
            })
            
            return {
                'success': True,
                'deleted_repository': repo_info,
                'message': f"Repository '{repository.name}' deleted successfully"
            }
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete Git repository: {str(e)}", extra={
                'repository_id': repository_id
            })
            raise DatabaseError(f"Failed to delete repository: {str(e)}")
    
    @log_function_call
    def verify_repository(self, repository_id: int) -> Tuple[bool, str]:
        """
        Verify repository access and update status.
        
        Args:
            repository_id: ID of the repository to verify
            
        Returns:
            Tuple of (is_verified, verification_message)
            
        Raises:
            NotFoundError: If repository doesn't exist
        """
        # Ensure repository exists
        self.get_repository(repository_id)
        
        # Delegate to git service
        return self.git_service.verify_repository(repository_id)
    
    @log_function_call
    def clone_repository(
        self,
        repository_id: int,
        target_directory: str,
        branch: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Clone a repository to the target directory.
        
        Args:
            repository_id: ID of the repository to clone
            target_directory: Directory to clone into
            branch: Optional branch to clone
            
        Returns:
            Tuple of (success, message)
            
        Raises:
            NotFoundError: If repository doesn't exist
            ValidationError: If validation fails
        """
        repository = self.get_repository(repository_id)
        
        return self.git_service.clone_repository(
            repository,
            target_directory,
            branch
        )
    
    @log_function_call
    def get_repository_info(self, repository_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a repository.
        
        Args:
            repository_id: ID of the repository
            
        Returns:
            Dictionary with repository information
            
        Raises:
            NotFoundError: If repository doesn't exist
        """
        self.get_repository(repository_id)  # Verify exists
        
        return self.git_service.get_repository_info(repository_id)
    
    @log_function_call
    def get_repositories_by_credential(self, credential_id: int) -> List[GitRepository]:
        """
        Get all repositories that use a specific credential.
        
        Args:
            credential_id: ID of the credential
            
        Returns:
            List of GitRepository instances
        """
        try:
            repositories = self.db.query(GitRepository).filter(
                GitRepository.credential_id == credential_id
            ).order_by(GitRepository.created_at.desc()).all()
            
            logger.debug(f"Retrieved {len(repositories)} repositories for credential", extra={
                'credential_id': credential_id
            })
            
            return repositories
            
        except Exception as e:
            logger.error(f"Failed to get repositories by credential: {str(e)}")
            raise DatabaseError(f"Failed to get repositories: {str(e)}")
    
    @log_function_call
    def verify_custom_repo_url(self, repository_url: str) -> Dict[str, Any]:
        """
        Validate a custom repository URL without saving it.
        
        Used for validation before creating a repository.
        Tests URL format and shows parsed information.
        
        Args:
            repository_url: Repository URL to validate
            
        Returns:
            Dictionary with validation results and parsed info
        """
        result = {
            'is_valid': False,
            'repository_type': None,
            'normalized_url': None,
            'error': None,
            'parsed_info': {}
        }
        
        try:
            if not repository_url or not repository_url.strip():
                result['error'] = "Repository URL is required"
                return result
            
            repository_url = repository_url.strip()
            
            # Validate URL format
            is_valid, repo_type, normalized_url = self.git_service.validate_repository_url(repository_url)
            
            result['is_valid'] = is_valid
            result['repository_type'] = repo_type
            result['normalized_url'] = normalized_url
            
            if not is_valid:
                result['error'] = normalized_url  # normalized_url contains error message
                return result
            
            # Parse URL for additional info
            from urllib.parse import urlparse
            
            parsed = urlparse(normalized_url)
            
            if repo_type == 'https':
                result['parsed_info'] = {
                    'host': parsed.netloc,
                    'owner': parsed.path.split('/')[1] if len(parsed.path.split('/')) > 1 else 'unknown',
                    'repo_name': parsed.path.split('/')[-1].replace('.git', '')
                }
            elif repo_type == 'ssh':
                # Parse SSH URL: git@host:owner/repo.git
                url_parts = normalized_url.split(':')
                if len(url_parts) >= 2:
                    host_part = url_parts[0].replace('git@', '')
                    repo_part = url_parts[1].replace('.git', '')
                    path_parts = repo_part.split('/')
                    
                    result['parsed_info'] = {
                        'host': host_part,
                        'owner': path_parts[0] if len(path_parts) > 1 else 'unknown',
                        'repo_name': path_parts[-1] if len(path_parts) > 0 else 'unknown'
                    }
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = f"Validation error: {str(e)}"
            logger.error(f"Error validating repository URL: {str(e)}")
        
        return result