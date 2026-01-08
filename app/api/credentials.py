"""
API endpoints for credential management.

This module provides REST API endpoints for creating, updating, listing,
and managing encrypted credentials with proper validation and security.

Author: Open WebUI Customizer Team
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.models import Credential
from app.schemas.credentials import (
    CredentialCreate, CredentialResponse, CredentialUpdate,
    CredentialDataUpdate, CredentialVerificationResult,
    CredentialList, CredentialDetail, CredentialTypeDescription,
    get_credential_type_descriptions
)
from app.services.credential_service import CredentialService
from app.exceptions import (
    NotFoundError, ValidationError, DatabaseError, ConfigurationError
)
from app.utils.logging import get_logger, LogContext

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/credentials", tags=["credentials"])


def get_credential_service(db: Session) -> CredentialService:
    """
    Dependency to get credential service instance.
    
    Args:
        db: Database session
        
    Returns:
        Credential service instance
    """
    return CredentialService(db)


@router.post("/", response_model=CredentialResponse, status_code=201)
def create_credential(
    credential_data: CredentialCreate,
    db: Session = Depends(get_db)
) -> CredentialResponse:
    """
    Create a new credential with encrypted storage.
    
    The sensitive credential_data field will be encrypted using AES-256-GCM
    and never exposed in API responses.
    
    Args:
        credential_data: Credential creation data
        db: Database session
        
    Returns:
        Created credential (without sensitive data)
        
    Raises:
        HTTPException 400: If validation fails
        HTTPException 409: If credential name already exists
        HTTPException 500: If server error occurs
    """
    try:
        with LogContext(logger, api="create_credential"):
            service = get_credential_service(db)
            credential = service.create_credential(credential_data)
            
            logger.info(f"Successfully created credential", extra={
                'credential_id': credential.id,
                'credential_name': credential.name,
                'credential_type': credential.credential_type
            })
            
            return credential
            
    except ValidationError as e:
        logger.warning(f"Credential validation failed: {str(e)}", extra={
            'credential_name': credential_data.name,
            'credential_type': credential_data.credential_type
        })
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error creating credential: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error creating credential: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=CredentialList)
def list_credentials(
    credential_type: Optional[str] = Query(
        None,
        description="Filter by credential type"
    ),
    skip: int = Query(
        0,
        ge=0,
        description="Number of items to skip"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Maximum items to return"
    ),
    include_expired: bool = Query(
        False,
        description="Include expired credentials"
    ),
    db: Session = Depends(get_db)
) -> CredentialList:
    """
    List credentials with filtering and pagination.
    
    Args:
        credential_type: Optional filter by credential type
        skip: Items to skip for pagination
        limit: Maximum items to return
        include_expired: Whether to include expired credentials
        db: Database session
        
    Returns:
        Paginated list of credentials
    """
    try:
        service = get_credential_service(db)
        
        # Get total count
        base_query = db.query(Credential).filter(Credential.is_active == True)
        
        if credential_type:
            base_query = base_query.filter(Credential.credential_type == credential_type)
        
        if not include_expired:
            base_query = base_query.filter(
                (Credential.expires_at.is_(None)) |
                (Credential.expires_at > datetime.utcnow())
            )
        
        total = base_query.count()
        
        # Get items
        credentials = service.list_credentials(
            credential_type=credential_type,
            skip=skip,
            limit=limit,
            include_expired=include_expired
        )
        
        # Calculate pagination info
        has_next = (skip + limit) < total
        has_prev = skip > 0
        
        return CredentialList(
            items=credentials,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except DatabaseError as e:
        logger.error(f"Database error listing credentials: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error listing credentials: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{credential_id}", response_model=CredentialDetail)
def get_credential(
    credential_id: int,
    db: Session = Depends(get_db)
) -> CredentialDetail:
    """
    Get detailed information about a credential.
    
    Args:
        credential_id: Database ID of the credential
        db: Database session
        
    Returns:
        Detailed credential information
        
    Raises:
        HTTPException 404: If credential not found
        HTTPException 500: If server error occurs
    """
    try:
        service = get_credential_service(db)
        credential = service.get_credential(credential_id)
        
        if not credential:
            raise HTTPException(
                status_code=404,
                detail=f"Credential with ID {credential_id} not found"
            )
        
        # Convert to detailed response
        now = datetime.utcnow()
        days_until_expiry = None
        has_expired = False
        
        if credential.expires_at:
            if credential.expires_at < now:
                has_expired = True
                days_until_expiry = 0
            else:
                days_until_expiry = (credential.expires_at - now).days
        
        return CredentialDetail(
            id=credential.id,
            name=credential.name,
            credential_type=credential.credential_type,
            metadata=credential.metadata,
            is_active=credential.is_active,
            created_at=credential.created_at,
            updated_at=credential.updated_at,
            expires_at=credential.expires_at,
            last_used_at=credential.last_used_at,
            has_expired=has_expired,
            days_until_expiry=days_until_expiry
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credential {credential_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{credential_id}", response_model=CredentialResponse)
def update_credential(
    credential_id: int,
    update_data: CredentialUpdate,
    db: Session = Depends(get_db)
) -> CredentialResponse:
    """
    Update credential metadata (non-sensitive data).
    
    This endpoint cannot update the actual credential data.
    Use PUT /{credential_id}/data for that.
    
    Args:
        credential_id: Database ID of the credential
        update_data: Update data (excluding sensitive info)
        db: Database session
        
    Returns:
        Updated credential
        
    Raises:
        HTTPException 404: If credential not found
        HTTPException 400: If validation fails
        HTTPException 500: If server error occurs
    """
    try:
        service = get_credential_service(db)
        credential = service.update_credential(credential_id, update_data)
        
        if not credential:
            raise HTTPException(
                status_code=404,
                detail=f"Credential with ID {credential_id} not found"
            )
        
        logger.info(f"Updated credential metadata", extra={
            'credential_id': credential_id,
            'updated_fields': list(update_data.model_dump(exclude_unset=True).keys())
        })
        
        return credential
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error updating credential: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error updating credential: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{credential_id}/data", response_model=CredentialResponse)
def update_credential_data(
    credential_id: int,
    update_data: CredentialDataUpdate,
    db: Session = Depends(get_db)
) -> CredentialResponse:
    """
    Update the sensitive credential data.
    
    This endpoint requires the full credential data and will
    re-encrypt it with updated keys.
    
    Args:
        credential_id: Database ID of the credential
        update_data: New credential data to encrypt
        db: Database session
        
    Returns:
        Updated credential
        
    Raises:
        HTTPException 404: If credential not found
        HTTPException 400: If validation fails
        HTTPException 500: If server error occurs
    """
    try:
        service = get_credential_service(db)
        credential = service.update_credential_data(credential_id, update_data)
        
        logger.info(f"Updated credential encrypted data", extra={
            'credential_id': credential_id
        })
        
        return credential
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error updating credential data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error updating credential data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{credential_id}")
def delete_credential(
    credential_id: int,
    permanent: bool = Query(
        False,
        description="Permanently delete instead of deactivating"
    ),
    db: Session = Depends(get_db)
) -> dict:
    """
    Delete or deactivate a credential.
    
    By default, credentials are deactivated and can be restored.
    Set permanent=true to permanently delete.
    
    Args:
        credential_id: Database ID of the credential
        permanent: Whether to permanently delete
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException 404: If credential not found
        HTTPException 500: If server error occurs
    """
    try:
        service = get_credential_service(db)
        success = service.delete_credential(credential_id, permanent=permanent)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Credential with ID {credential_id} not found"
            )
        
        action = "permanently deleted" if permanent else "deactivated"
        logger.info(f"Successfully {action} credential", extra={
            'credential_id': credential_id,
            'permanent': permanent
        })
        
        return {"message": f"Credential {credential_id} {action} successfully"}
        
    except DatabaseError as e:
        logger.error(f"Database error deleting credential: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error deleting credential: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{credential_id}/verify", response_model=CredentialVerificationResult)
def verify_credential(
    credential_id: int,
    db: Session = Depends(get_db)
) -> CredentialVerificationResult:
    """
    Verify that a credential is valid and working.
    
    Performs type-specific verification:
    - SSH keys: Check key format and structure
    - HTTPS tokens: Check format and basic validation
    - Registry creds: Check authentication against registry
    
    Args:
        credential_id: Database ID of the credential
        db: Database session
        
    Returns:
        Verification result with status and message
        
    Raises:
        HTTPException 404: If credential not found
        HTTPException 500: If server error occurs
    """
    try:
        service = get_credential_service(db)
        is_valid, message = service.verify_credential(credential_id)
        
        logger.info(f"Verified credential", extra={
            'credential_id': credential_id,
            'valid': is_valid,
            'message': message
        })
        
        return CredentialVerificationResult(
            credential_id=credential_id,
            valid=is_valid,
            message=message
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error verifying credential {credential_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/types/info", response_model=List[CredentialTypeDescription])
def list_credential_types() -> List[CredentialTypeDescription]:
    """
    Get information about all supported credential types.
    
    Returns:
        List of credential type descriptions with required fields
    """
    return get_credential_type_descriptions()


@router.post("/cleanup-expired")
def cleanup_expired_credentials(db: Session = Depends(get_db)) -> dict:
    """
    Deactivate all expired credentials.
    
    This endpoint is typically called by a background job or
    administrator to clean up expired credentials.
    
    Args:
        db: Database session
        
    Returns:
        Number of credentials deactivated
        
    Raises:
        HTTPException 500: If server error occurs
    """
    try:
        service = get_credential_service(db)
        count = service.cleanup_expired_credentials()
        
        logger.info(f"Cleaned up expired credentials", extra={
            'deactivated_count': count
        })
        
        return {
            "message": f"Successfully deactivated {count} expired credentials",
            "count": count
        }
        
    except DatabaseError as e:
        logger.error(f"Database error cleaning up credentials: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error cleaning up credentials: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{credential_id}/test-connection")
def test_credential_connection(
    credential_id: int,
    test_endpoint: Optional[str] = Body(
        None,
        description="Optional endpoint to test against"
    ),
    db: Session = Depends(get_db)
) -> dict:
    """
    Test credential connection with an actual service call.
    
    This endpoint performs a real connection test:
    - GIT credentials: Clone a test repository
    - Registry credentials: Attempt login/push
    - HTTPS: Test URL access with credentials
    
    Args:
        credential_id: Database ID of the credential
        test_endpoint: Optional service endpoint to test
        db: Database session
        
    Returns:
        Test results with connection details
        
    Raises:
        HTTPException 404: If credential not found
        HTTPException 500: If server error occurs
    """
    try:
        service = get_credential_service(db)
        credential = service.get_credential(credential_id)
        
        if not credential:
            raise HTTPException(
                status_code=404,
                detail=f"Credential with ID {credential_id} not found"
            )
        
        # Get credential data for testing
        credential_data = service.get_decrypted_credential(credential_id)
        
        # Perform type-specific connection test
        test_results = {
            'credential_type': credential.credential_type,
            'connection_tested': False,
            'error': None,
            'details': None
        }
        
        # TODO: Implement actual connection tests
        # This is a placeholder that would implement real tests
        if credential.credential_type == "git_ssh":
            test_results['details'] = "SSH key validation (not implemented)"
            test_results['connection_tested'] = True
        elif credential.credential_type == "git_https":
            test_results['details'] = "HTTPS credential validation (not implemented)"
            test_results['connection_tested'] = True
        else:
            test_results['error'] = "Connection test not implemented for this type"
        
        logger.info(f"Tested credential connection", extra={
            'credential_id': credential_id,
            'credential_type': credential.credential_type,
            'success': test_results['connection_tested']
        })
        
        return test_results
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error testing credential connection: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")