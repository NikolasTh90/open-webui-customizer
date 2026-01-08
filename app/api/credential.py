"""
API routes for credential management.

This module provides REST API endpoints for managing encrypted credentials,
including CRUD operations and verification endpoints.

Author: Open WebUI Customizer Team
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.config import get_settings
from app.models.database import get_db
from app.services.credential_service import CredentialService
from app.models.models import Credential
from app.exceptions import (
    ValidationError, NotFoundError, DatabaseError,
    DuplicateResourceError
)
from app.utils.logging import get_logger, log_function_call, log_api_request
from app.utils.validators import validate_required_fields, sanitize_string_input

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/credentials", tags=["credentials"])

# Pydantic models for request/response
class CredentialResponse(BaseModel):
    id: int
    name: str
    credential_type: str
    metadata: Dict[str, Any]
    is_active: bool
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None

class CredentialCreate(BaseModel):
    name: str
    credential_type: str
    credential_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = {}
    expires_at: Optional[str] = None

class CredentialUpdate(BaseModel):
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None
    is_active: Optional[bool] = None

class CredentialDataUpdate(BaseModel):
    credential_data: Dict[str, Any]

# Initialize services
def get_credential_service(db: Session) -> CredentialService:
    """Get credential service instance."""
    return CredentialService(db)

@router.get("/", response_model=List[CredentialResponse])
@log_api_request
@log_function_call
def get_credentials(
    credential_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_expired: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Get all credentials.
    
    Query Parameters:
        credential_type (str): Filter by credential type
        skip (int): Number of records to skip (pagination)
        limit (int): Maximum number of records to return
        include_expired (bool): Whether to include expired credentials
    
    Returns:
        JSON array of credential data (without sensitive data)
    """
    try:
        service = get_credential_service(db)
        
        # Validate pagination parameters
        from app.utils.validators import validate_pagination_params
        skip, limit = validate_pagination_params(skip, limit)
        
        credentials = service.list_credentials(
            credential_type=credential_type,
            skip=skip,
            limit=limit,
            include_expired=include_expired
        )
        
        result = []
        for cred in credentials:
            result.append(CredentialResponse(
                id=cred.id,  # type: ignore[arg-type]
                name=cred.name,  # type: ignore[arg-type]
                credential_type=cred.credential_type,  # type: ignore[arg-type]
                metadata=cred.metadata or {},  # type: ignore[arg-type]
                is_active=cred.is_active,  # type: ignore[arg-type]
                created_at=cred.created_at.isoformat(),  # type: ignore[arg-type]
                updated_at=cred.updated_at.isoformat(),  # type: ignore[arg-type]
                expires_at=cred.expires_at.isoformat() if cred.expires_at else None,  # type: ignore[arg-type]
                last_used_at=cred.last_used_at.isoformat() if cred.last_used_at else None  # type: ignore[arg-type]
            ))
        
        return result
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error getting credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=CredentialResponse, status_code=201)
@log_api_request
@log_function_call
def create_credential(
    credential_data: CredentialCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new encrypted credential.
    
    Required JSON Body:
        name (str): Credential name
        credential_type (str): Type of credential
        credential_data (dict): Sensitive credential data
    
    Optional JSON Body:
        metadata (dict): Non-sensitive metadata
        expires_at (str): ISO datetime string for expiration
    
    Returns:
        JSON of created credential data (without sensitive data)
    """
    try:
        # Validate required fields
        validate_required_fields(credential_data.dict(), ['name', 'credential_type', 'credential_data'])
        
        # Validate credential type
        from app.utils.validators import validate_credential_type
        validate_credential_type(credential_data.credential_type)
        
        # Validate credential data structure
        from app.utils.validators import validate_json_structure
        validate_json_structure(credential_data.credential_data)
        
        # Parse expiration date if provided
        expires_at = None
        if credential_data.expires_at:
            from datetime import datetime
            try:
                expires_at = datetime.fromisoformat(credential_data.expires_at.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError("Invalid expiration date format. Use ISO format.")
        
        # Create credential using service
        service = get_credential_service(db)
        credential = service.create_credential(credential_data)
        
        logger.info(f"Created credential via API", extra={
            'credential_id': credential.id,
            'name': credential.name
        })
        
        return CredentialResponse(
            id=credential.id,  # type: ignore[arg-type]
            name=credential.name,  # type: ignore[arg-type]
            credential_type=credential.credential_type,  # type: ignore[arg-type]
            metadata=credential.metadata or {},  # type: ignore[arg-type]
            is_active=credential.is_active,  # type: ignore[arg-type]
            created_at=credential.created_at.isoformat(),  # type: ignore[arg-type]
            updated_at=credential.updated_at.isoformat(),  # type: ignore[arg-type]
            expires_at=credential.expires_at.isoformat() if credential.expires_at else None  # type: ignore[arg-type]
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateResourceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error creating credential: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating credential: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{credential_id}", response_model=CredentialResponse)
@log_api_request
@log_function_call
def get_credential(
    credential_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific credential.
    
    URL Parameters:
        credential_id (int): Credential ID
    
    Returns:
        JSON of credential data (without sensitive data)
    """
    try:
        service = get_credential_service(db)
        credential = service.get_credential(credential_id)
        
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        return CredentialResponse(
            id=credential.id,  # type: ignore[arg-type]
            name=credential.name,  # type: ignore[arg-type]
            credential_type=credential.credential_type,  # type: ignore[arg-type]
            metadata=credential.metadata or {},  # type: ignore[arg-type]
            is_active=credential.is_active,  # type: ignore[arg-type]
            created_at=credential.created_at.isoformat(),  # type: ignore[arg-type]
            updated_at=credential.updated_at.isoformat(),  # type: ignore[arg-type]
            expires_at=credential.expires_at.isoformat() if credential.expires_at else None,  # type: ignore[arg-type]
            last_used_at=credential.last_used_at.isoformat() if credential.last_used_at else None  # type: ignore[arg-type]
        )
        
    except DatabaseError as e:
        logger.error(f"Database error getting credential: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting credential: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{credential_id}", response_model=CredentialResponse)
@log_api_request
@log_function_call
def update_credential(
    credential_id: int,
    credential_update: CredentialUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a credential's non-sensitive data.
    
    URL Parameters:
        credential_id (int): Credential ID
    
    JSON Body (all fields optional):
        name (str): New name
        metadata (dict): New metadata
        expires_at (str): New expiration date (ISO format)
        is_active (bool): Active status
    
    Returns:
        JSON of updated credential data
    """
    try:
        # Validate metadata if provided
        if credential_update.metadata is not None and not isinstance(credential_update.metadata, dict):
            raise ValidationError("Metadata must be a dictionary")
        
        # Parse expiration date if provided
        if credential_update.expires_at is not None:
            if credential_update.expires_at:
                from datetime import datetime
                try:
                    # Store the datetime in a local variable for the service
                    expires_at_datetime = datetime.fromisoformat(credential_update.expires_at.replace('Z', '+00:00'))
                except ValueError:
                    raise ValidationError("Invalid expiration date format. Use ISO format.")
            else:
                credential_update.expires_at = None
        
        service = get_credential_service(db)
        # Create a proper update dict for the service
        update_dict = credential_update.dict(exclude_unset=True)
        if 'expires_at' in update_dict and credential_update.expires_at is not None:
            update_dict['expires_at'] = expires_at_datetime
        
        credential = service.update_credential(credential_id, update_dict)
        
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        logger.info(f"Updated credential via API", extra={
            'credential_id': credential.id,
            'name': credential.name
        })
        
        return CredentialResponse(
            id=credential.id,  # type: ignore[arg-type]
            name=credential.name,  # type: ignore[arg-type]
            credential_type=credential.credential_type,  # type: ignore[arg-type]
            metadata=credential.metadata or {},  # type: ignore[arg-type]
            is_active=credential.is_active,  # type: ignore[arg-type]
            created_at=credential.created_at.isoformat(),  # type: ignore[arg-type]
            updated_at=credential.updated_at.isoformat(),  # type: ignore[arg-type]
            expires_at=credential.expires_at.isoformat() if credential.expires_at else None,  # type: ignore[arg-type]
            last_used_at=credential.last_used_at.isoformat() if credential.last_used_at else None  # type: ignore[arg-type]
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error updating credential: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating credential: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{credential_id}")
@log_api_request
@log_function_call
def delete_credential(
    credential_id: int,
    permanent: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Delete or deactivate a credential.
    
    URL Parameters:
        credential_id (int): Credential ID
    
    Query Parameters:
        permanent (bool): If true, permanently delete; if false, deactivate
    
    Returns:
        JSON confirming deletion
    """
    try:
        service = get_credential_service(db)
        success = service.delete_credential(credential_id, permanent=permanent)
        
        if not success:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        action = "permanently deleted" if permanent else "deactivated"
        
        logger.info(f"Deleted credential via API", extra={
            'credential_id': credential_id,
            'permanent': permanent
        })
        
        return {"success": True, "message": f"Credential {action} successfully"}
        
    except DatabaseError as e:
        logger.error(f"Database error deleting credential: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting credential: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{credential_id}/verify")
@log_api_request
@log_function_call
def verify_credential(
    credential_id: int,
    db: Session = Depends(get_db)
):
    """
    Verify that a credential is valid and working.
    
    URL Parameters:
        credential_id (int): Credential ID
    
    Returns:
        JSON with verification status
    """
    try:
        service = get_credential_service(db)
        is_valid, message = service.verify_credential(credential_id)
        
        logger.info(f"Verified credential via API", extra={
            'credential_id': credential_id,
            'is_valid': is_valid
        })
        
        return {
            "success": True,
            "is_valid": is_valid,
            "message": message
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error verifying credential: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{credential_id}/data", response_model=CredentialResponse)
@log_api_request
@log_function_call
def update_credential_data(
    credential_id: int,
    data_update: CredentialDataUpdate,
    db: Session = Depends(get_db)
):
    """
    Update the sensitive credential data.
    
    URL Parameters:
        credential_id (int): Credential ID
    
    Required JSON Body:
        credential_data (dict): New sensitive credential data
    
    Returns:
        JSON of updated credential (without sensitive data)
    """
    try:
        # Validate credential data structure
        from app.utils.validators import validate_json_structure
        validate_json_structure(data_update.credential_data)
        
        # Import the proper schema type from schemas
        from app.schemas.credentials import CredentialDataUpdate as SchemaCredentialDataUpdate
        
        # Convert to the proper schema type (only credential_data is needed)
        schema_update = SchemaCredentialDataUpdate(
            credential_data=data_update.credential_data
        )
        
        service = get_credential_service(db)
        credential = service.update_credential_data(credential_id, schema_update)
        
        logger.info(f"Updated credential data via API", extra={
            'credential_id': credential_id,
            'name': credential.name
        })
        
        return CredentialResponse(
            id=credential.id,  # type: ignore[arg-type]
            name=credential.name,  # type: ignore[arg-type]
            credential_type=credential.credential_type,  # type: ignore[arg-type]
            metadata=credential.metadata or {},  # type: ignore[arg-type]
            is_active=credential.is_active,  # type: ignore[arg-type]
            created_at=credential.created_at.isoformat(),  # type: ignore[arg-type]
            updated_at=credential.updated_at.isoformat(),  # type: ignore[arg-type]
            expires_at=credential.expires_at.isoformat() if credential.expires_at else None,  # type: ignore[arg-type]
            last_used_at=credential.last_used_at.isoformat() if credential.last_used_at else None  # type: ignore[arg-type]
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error updating credential data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating credential data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types", response_model=List[Dict[str, str]])
@log_api_request
@log_function_call
def get_credential_types():
    """
    Get all supported credential types.
    
    Returns:
        JSON array of supported credential types with descriptions
    """
    try:
        from app.schemas.credentials import CredentialType
        
        types = []
        for cred_type in CredentialType:
            types.append({
                'value': cred_type.value,
                'display_name': cred_type.value.replace('_', ' ').title(),
                'description': _get_credential_type_description(cred_type.value)
            })
        
        return types
        
    except Exception as e:
        logger.error(f"Error getting credential types: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_credential_type_description(credential_type: str) -> str:
    """Get description for a credential type."""
    descriptions = {
        'git_ssh': 'SSH key for Git repository access',
        'git_https': 'HTTPS credentials (username/token) for Git repository access',
        'registry_docker_hub': 'Docker Hub registry credentials',
        'registry_aws_ecr': 'Amazon ECR registry credentials',
        'registry_quay_io': 'Quay.io registry credentials'
    }
    return descriptions.get(credential_type, 'Unknown credential type')