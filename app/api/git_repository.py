"""
API routes for Git repository management.

This module provides REST API endpoints for managing Git repositories,
including CRUD operations, verification, and testing operations.

Author: Open WebUI Customizer Team
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.config import get_settings
from app.models.database import get_db
from app.services.git_repository_service import GitRepositoryService
from app.models.models import GitRepository, Credential
from app.exceptions import (
    ValidationError, NotFoundError, DatabaseError
)
from app.utils.logging import get_logger, log_function_call, log_api_request
from app.utils.validators import validate_required_fields, validate_url_format

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/repositories", tags=["repositories"])

# Pydantic models for request/response
class GitRepositoryResponse(BaseModel):
    id: int
    name: str
    repository_url: str
    repository_type: str
    default_branch: str
    credential_id: Optional[int] = None
    is_experimental: bool
    description: Optional[str] = None
    is_verified: bool
    verification_status: str
    verification_message: Optional[str] = None
    created_at: str
    updated_at: str

class GitRepositoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    repository_url: str = Field(..., min_length=1)
    credential_id: Optional[int] = None
    default_branch: str = "main"
    is_experimental: bool = False
    description: Optional[str] = None

class GitRepositoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    credential_id: Optional[int] = None
    default_branch: Optional[str] = None
    is_experimental: Optional[bool] = None
    description: Optional[str] = None

class RepositoryValidationRequest(BaseModel):
    repository_url: str

class TestCloneRequest(BaseModel):
    branch: Optional[str] = None

class RepositoryListResponse(BaseModel):
    success: bool
    repositories: List[GitRepositoryResponse]
    count: int

class RepositoryResponse(BaseModel):
    success: bool
    repository: GitRepositoryResponse

class VerificationResponse(BaseModel):
    success: bool
    is_verified: bool
    message: str

class RepositoryInfoResponse(BaseModel):
    success: bool
    repository_info: Dict[str, Any]

class ValidationResponse(BaseModel):
    success: bool
    validation_result: Dict[str, Any]

class CredentialResponse(BaseModel):
    id: int
    name: str
    credential_type: str
    created_at: str

class CredentialsListResponse(BaseModel):
    success: bool
    credentials: List[CredentialResponse]
    count: int

class TestCloneResponse(BaseModel):
    success: bool
    test_result: Dict[str, Any]

class DeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_repository: Dict[str, Any]

# Initialize services
def get_git_repository_service(db: Session) -> GitRepositoryService:
    """Get Git repository service instance."""
    return GitRepositoryService(db)

def _repository_to_response(repo: GitRepository) -> GitRepositoryResponse:
    """Convert repository model to response model."""
    return GitRepositoryResponse(
        id=repo.id,  # type: ignore[arg-type]
        name=repo.name,  # type: ignore[arg-type]
        repository_url=repo.repository_url,  # type: ignore[arg-type]
        repository_type=repo.repository_type,  # type: ignore[arg-type]
        default_branch=repo.default_branch,  # type: ignore[arg-type]
        credential_id=repo.credential_id,  # type: ignore[arg-type]
        is_experimental=repo.is_experimental,  # type: ignore[arg-type]
        description=repo.description,  # type: ignore[arg-type]
        is_verified=repo.is_verified,  # type: ignore[arg-type]
        verification_status=repo.verification_status,  # type: ignore[arg-type]
        verification_message=repo.verification_message,  # type: ignore[arg-type]
        created_at=repo.created_at.isoformat(),  # type: ignore[arg-type]
        updated_at=repo.updated_at.isoformat()  # type: ignore[arg-type]
    )

@router.get("/", response_model=RepositoryListResponse)
@log_api_request
@log_function_call
def get_repositories(
    include_experimental: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Get all Git repositories.
    
    Query Parameters:
        include_experimental (bool): Include experimental repositories
    
    Returns:
        JSON array of repository data
    """
    try:
        service = get_git_repository_service(db)
        repositories = service.get_all_repositories(include_experimental)
        
        result = [_repository_to_response(repo) for repo in repositories]
        
        return RepositoryListResponse(
            success=True,
            repositories=result,
            count=len(result)
        )
        
    except DatabaseError as e:
        logger.error(f"Database error getting repositories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting repositories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=RepositoryResponse, status_code=201)
@log_api_request
@log_function_call
def create_repository(
    repository_data: GitRepositoryCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Git repository.
    
    Required JSON Body:
        name (str): Repository name
        repository_url (str): Repository URL
    
    Optional JSON Body:
        credential_id (int): Credential ID for authentication
        default_branch (str): Default branch (main/master/develop)
        is_experimental (bool): Whether this is experimental
        description (str): Repository description
    
    Returns:
        JSON of created repository data
    """
    try:
        service = get_git_repository_service(db)
        repository = service.create_repository(
            name=repository_data.name,
            repository_url=repository_data.repository_url,
            credential_id=repository_data.credential_id,
            default_branch=repository_data.default_branch,
            is_experimental=repository_data.is_experimental,
            description=repository_data.description.strip() if repository_data.description else None
        )
        
        logger.info(f"Created repository via API", extra={
            'repository_id': repository.id,
            'name': repository.name
        })
        
        return RepositoryResponse(
            success=True,
            repository=_repository_to_response(repository)
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error creating repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{repository_id}", response_model=RepositoryResponse)
@log_api_request
@log_function_call
def get_repository(
    repository_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific Git repository.
    
    URL Parameters:
        repository_id (int): Repository ID
    
    Returns:
        JSON of repository data
    """
    try:
        service = get_git_repository_service(db)
        repository = service.get_repository(repository_id)
        
        return RepositoryResponse(
            success=True,
            repository=_repository_to_response(repository)
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error getting repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{repository_id}", response_model=RepositoryResponse)
@log_api_request
@log_function_call
def update_repository(
    repository_id: int,
    repository_data: GitRepositoryUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a Git repository.
    
    URL Parameters:
        repository_id (int): Repository ID
    
    JSON Body (all fields optional):
        name (str): Repository name
        credential_id (int): Credential ID (or 0 to remove)
        default_branch (str): Default branch
        is_experimental (bool): Whether this is experimental
        description (str): Repository description
    
    Returns:
        JSON of updated repository data
    """
    try:
        service = get_git_repository_service(db)
        repository = service.update_repository(
            repository_id=repository_id,
            name=repository_data.name,
            credential_id=repository_data.credential_id,
            default_branch=repository_data.default_branch,
            is_experimental=repository_data.is_experimental,
            description=repository_data.description.strip() if repository_data.description else None
        )
        
        logger.info(f"Updated repository via API", extra={
            'repository_id': repository.id,
            'name': repository.name
        })
        
        return RepositoryResponse(
            success=True,
            repository=_repository_to_response(repository)
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error updating repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{repository_id}", response_model=DeleteResponse)
@log_api_request
@log_function_call
def delete_repository(
    repository_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a Git repository.
    
    URL Parameters:
        repository_id (int): Repository ID
    
    Returns:
        JSON confirming deletion
    """
    try:
        service = get_git_repository_service(db)
        result = service.delete_repository(repository_id)
        
        logger.info(f"Deleted repository via API", extra={
            'repository_id': repository_id
        })
        
        return DeleteResponse(
            success=True,
            message=result['message'],
            deleted_repository=result['deleted_repository']
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error deleting repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{repository_id}/verify", response_model=VerificationResponse)
@log_api_request
@log_function_call
def verify_repository(
    repository_id: int,
    db: Session = Depends(get_db)
):
    """
    Verify repository access.
    
    URL Parameters:
        repository_id (int): Repository ID
    
    Returns:
        JSON with verification status
    """
    try:
        service = get_git_repository_service(db)
        is_verified, message = service.verify_repository(repository_id)
        
        logger.info(f"Verified repository via API", extra={
            'repository_id': repository_id,
            'is_verified': is_verified
        })
        
        return VerificationResponse(
            success=True,
            is_verified=is_verified,
            message=message
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error verifying repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{repository_id}/info", response_model=RepositoryInfoResponse)
@log_api_request
@log_function_call
def get_repository_info(
    repository_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a repository.
    
    URL Parameters:
        repository_id (int): Repository ID
    
    Returns:
        JSON with detailed repository information
    """
    try:
        service = get_git_repository_service(db)
        info = service.get_repository_info(repository_id)
        
        return RepositoryInfoResponse(
            success=True,
            repository_info=info
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting repository info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-url", response_model=ValidationResponse)
@log_api_request
@log_function_call
def validate_repository_url(
    validation_request: RepositoryValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Validate a repository URL without creating a repository.
    
    JSON Body:
        repository_url (str): Repository URL to validate
    
    Returns:
        JSON with validation results and parsed information
    """
    try:
        service = get_git_repository_service(db)
        result = service.verify_custom_repo_url(validation_request.repository_url)
        
        return ValidationResponse(
            success=True,
            validation_result=result
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error validating repository URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available-credentials", response_model=CredentialsListResponse)
@log_api_request
@log_function_call
def get_available_credentials(
    db: Session = Depends(get_db)
):
    """
    Get all available credentials for repository configuration.
    
    Returns:
        JSON array of available credentials
    """
    try:
        credentials = db.query(Credential).order_by(Credential.name).all()
        
        result = []
        for cred in credentials:
            result.append(CredentialResponse(
                id=cred.id,  # type: ignore[arg-type]
                name=cred.name,  # type: ignore[arg-type]
                credential_type=cred.credential_type,  # type: ignore[arg-type]
                created_at=cred.created_at.isoformat()  # type: ignore[arg-type]
            ))
        
        return CredentialsListResponse(
            success=True,
            credentials=result,
            count=len(result)
        )
        
    except Exception as e:
        logger.error(f"Error getting available credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{repository_id}/test-clone", response_model=TestCloneResponse)
@log_api_request
@log_function_call
def test_repository_clone(
    repository_id: int,
    test_request: TestCloneRequest,
    db: Session = Depends(get_db)
):
    """
    Test cloning a repository to a temporary directory.
    
    This endpoint performs a test clone to verify the repository
    can be cloned with the current credentials. The clone is
    immediately deleted after verification.
    
    URL Parameters:
        repository_id (int): Repository ID
    
    Optional JSON Body:
        branch (str): Branch to test (uses default if not specified)
    
    Returns:
        JSON with test clone results
    """
    try:
        # Create temporary directory for test
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            service = get_git_repository_service(db)
            success, message = service.clone_repository(
                repository_id,
                temp_dir,
                test_request.branch
            )
        
        logger.info(f"Test clone completed", extra={
            'repository_id': repository_id,
            'success': success
        })
        
        return TestCloneResponse(
            success=True,
            test_result={
                'success': success,
                'message': message
            }
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error testing repository clone: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))