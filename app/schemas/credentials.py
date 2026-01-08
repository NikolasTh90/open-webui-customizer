"""
Pydantic schemas for credential management.

This module defines the request/response models for credential operations,
including creation, updating, and listing credentials with proper validation.

Author: Open WebUI Customizer Team
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator, Extra

from app.utils.logging import get_logger

logger = get_logger(__name__)


class CredentialType(str, Enum):
    """Supported credential types for different services."""
    
    GIT_SSH = "git_ssh"
    GIT_HTTPS = "git_https"
    REGISTRY_DOCKER_HUB = "registry_docker_hub"
    REGISTRY_AWS_ECR = "registry_aws_ecr"
    REGISTRY_QUAY_IO = "registry_quay_io"
    REGISTRY_GENERIC = "registry_generic"


class CredentialStatus(str, Enum):
    """Credential validation status."""
    
    UNKNOWN = "unknown"
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"


# Credential field definitions for validation
CREDENTIAL_FIELD_DEFINITIONS = {
    CredentialType.GIT_SSH: {
        "required": ["private_key"],
        "optional": ["passphrase", "known_hosts"],
        "description": "SSH key for Git repository access"
    },
    CredentialType.GIT_HTTPS: {
        "required": ["username", "password_or_token"],
        "optional": [],
        "description": "HTTPS credentials for Git repository"
    },
    CredentialType.REGISTRY_DOCKER_HUB: {
        "required": ["username", "access_token"],
        "optional": [],
        "description": "Docker Hub registry credentials"
    },
    CredentialType.REGISTRY_AWS_ECR: {
        "required": ["aws_access_key_id", "aws_secret_access_key"],
        "optional": ["aws_session_token", "region"],
        "description": "AWS ECR registry credentials"
    },
    CredentialType.REGISTRY_QUAY_IO: {
        "required": ["username", "password"],
        "optional": [],
        "description": "Red Hat Quay.io registry credentials"
    },
    CredentialType.REGISTRY_GENERIC: {
        "required": ["username", "password_or_token"],
        "optional": ["registry_url"],
        "description": "Generic Docker registry credentials"
    }
}


class CredentialBase(BaseModel):
    """Base schema for credential operations."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable name for the credential"
    )
    credential_type: CredentialType = Field(
        ...,
        description="Type of credential being stored"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Non-sensitive metadata about the credential"
    )


class CredentialCreate(CredentialBase):
    """Schema for creating a new credential."""
    
    credential_data: Dict[str, Any] = Field(
        ...,
        description="Sensitive credential data (will be encrypted)"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Optional expiration date for the credential"
    )
    
    @validator('credential_data')
    def validate_credential_data(cls, v: Dict[str, Any], values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that credential data contains required fields for the type.
        
        Args:
            v: Credential data dictionary
            values: Other field values including credential_type
            
        Returns:
            Validated credential data
            
        Raises:
            ValueError: If required fields are missing or validation fails
        """
        credential_type = values.get('credential_type')
        
        if not credential_type:
            raise ValueError("credential_type must be specified")
        
        # Get field definitions for the credential type
        field_defs = CREDENTIAL_FIELD_DEFINITIONS.get(credential_type)
        if not field_defs:
            logger.warning(f"Unknown credential type: {credential_type}")
        
        # Check required fields
        required_fields = field_defs.get('required', [])
        missing_fields = [field for field in required_fields if field not in v]
        
        if missing_fields:
            raise ValueError(
                f"Missing required fields for {credential_type}: {missing_fields}"
            )
        
        # Validate specific data formats
        if credential_type == CredentialType.GIT_SSH:
            cls._validate_ssh_key(v.get('private_key', ''))
        
        if credential_type == CredentialType.REGISTRY_AWS_ECR:
            cls._validate_aws_credentials(v)
        
        return v
    
    @staticmethod
    def _validate_ssh_key(private_key: str) -> None:
        """
        Validate SSH private key format.
        
        Args:
            private_key: SSH private key string
            
        Raises:
            ValueError: If key format is invalid
        """
        if not private_key.strip():
            raise ValueError("SSH private key cannot be empty")
        
        # Check for SSH key markers
        valid_markers = [
            '-----BEGIN OPENSSH PRIVATE KEY-----',
            '-----BEGIN RSA PRIVATE KEY-----',
            '-----BEGIN DSA PRIVATE KEY-----',
            '-----BEGIN EC PRIVATE KEY-----',
            '-----BEGIN PGP PRIVATE KEY BLOCK-----'
        ]
        
        has_valid_marker = any(marker in private_key for marker in valid_markers)
        if not has_valid_marker:
            logger.warning("SSH key may have invalid format")
            # Don't fail validation as there are SSH key formats without markers
    
    @staticmethod
    def _validate_aws_credentials(data: Dict[str, Any]) -> None:
        """
        Validate AWS credentials format.
        
        Args:
            data: AWS credential data
            
        Raises:
            ValueError: If format is invalid
        """
        access_key = data.get('aws_access_key_id', '')
        secret_key = data.get('aws_secret_access_key', '')
        
        # AWS access key pattern (starts with ASIA, AKIA, or similar)
        if not (access_key.startswith(('AKIA', 'ASIA', 'AKIAIOS')) and len(access_key) >= 16):
            raise ValueError("Invalid AWS access key ID format")
        
        #AWS secret key should be at least 40 characters
        if len(secret_key) < 40:
            raise ValueError("AWS secret access key appears too short")


class CredentialUpdate(BaseModel):
    """Schema for updating an existing credential."""
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="New name for the credential"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Updated metadata"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Update expiration date"
    )
    
    class Config:
        """Pydantic configuration."""
        extra = Extra.forbid  # Prevent extra fields


class CredentialDataUpdate(BaseModel):
    """Schema for updating credential data (requires re-encryption)."""
    
    credential_data: Dict[str, Any] = Field(
        ...,
        description="New credential data (will be encrypted)"
    )
    
    @validator('credential_data')
    def validate_credential_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate credential data format.
        
        Args:
            v: Credential data to validate
            
        Returns:
            Validated credential data
            
        Raises:
            ValueError: If validation fails
        """
        if not v:
            raise ValueError("Credential data cannot be empty")
        
        return v


class CredentialResponse(CredentialBase):
    """Schema for credential responses (without sensitive data)."""
    
    id: int = Field(..., description="Database ID of the credential")
    is_active: bool = Field(..., description="Whether the credential is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    verification_status: Optional[CredentialStatus] = Field(
        None,
        description="Last known verification status"
    )
    
    # Note: credential_data is NEVER exposed in responses for security
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class CredentialDetail(CredentialResponse):
    """Extended credential schema with additional metadata."""
    
    credential_type_name: str = Field(..., description="Human-readable credential type")
    description: Optional[str] = Field(None, description="Credential description")
    has_expired: bool = Field(..., description="Whether the credential has expired")
    days_until_expiry: Optional[int] = Field(
        None,
        description="Days until expiration (None if no expiration)"
    )
    
    @validator('credential_type_name', pre=True, always=True)
    def set_credential_type_name(cls, v: Any, values: Dict[str, Any]) -> str:
        """
        Set human-readable credential type name.
        
        Args:
            v: Existing value (ignore)
            values: Field values including credential_type
            
        Returns:
            Human-readable type name
        """
        credential_type = values.get('credential_type')
        if credential_type:
            return credential_type.replace('_', ' ').title()
        return "Unknown"
    
    @validator('has_expired', pre=True, always=True)
    def set_has_expired(cls, v: Any, values: Dict[str, Any]) -> bool:
        """
        Calculate if credential has expired.
        
        Args:
            v: Existing value (ignore)
            values: Field values including expires_at
            
        Returns:
            True if expired, False otherwise
        """
        expires_at = values.get('expires_at')
        if expires_at:
            return expires_at < datetime.utcnow()
        return False
    
    @validator('days_until_expiry', pre=True, always=True)
    def set_days_until_expiry(cls, v: Any, values: Dict[str, Any]) -> Optional[int]:
        """
        Calculate days until expiration.
        
        Args:
            v: Existing value (ignore)
            values: Field values including expires_at
            
        Returns:
            Days until expiration or None if no expiration
        """
        expires_at = values.get('expires_at')
        if expires_at:
            delta = expires_at - datetime.utcnow()
            return max(0, delta.days)
        return None


class CredentialVerificationResult(BaseModel):
    """Schema for credential verification results."""
    
    credential_id: int = Field(..., description="ID of the verified credential")
    valid: bool = Field(..., description="Whether the credential is valid")
    message: str = Field(..., description="Verification message")
    error_details: Optional[str] = Field(None, description="Error details if invalid")
    verification_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="When verification was performed"
    )


class CredentialList(BaseModel):
    """Schema for list of credentials with metadata."""
    
    items: List[CredentialResponse] = Field(..., description="List of credentials")
    total: int = Field(..., description="Total number of credentials")
    page: int = Field(default=1, description="Current page number")
    per_page: int = Field(default=50, description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class CredentialTypeDescription(BaseModel):
    """Schema describing a credential type and its fields."""
    
    type: CredentialType = Field(..., description="Credential type value")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Description of the credential type")
    required_fields: List[str] = Field(..., description="Required field names")
    optional_fields: List[str] = Field(..., description="Optional field names")
    field_descriptions: Dict[str, str] = Field(..., description="Field descriptions")


# Helper function to get credential type information
def get_credential_type_descriptions() -> List[CredentialTypeDescription]:
    """
    Get descriptions of all supported credential types.
    
    Returns:
        List of credential type descriptions
    """
    descriptions = []
    
    field_descriptions = {
        "private_key": "SSH private key for Git repository access",
        "passphrase": "Optional passphrase for SSH private key",
        "known_hosts": "SSH known hosts entries for Git server",
        "username": "Username for authentication",
        "password_or_token": "Password or access token for authentication",
        "access_token": "Access token for registry authentication",
        "aws_access_key_id": "AWS access key ID for ECR",
        "aws_secret_access_key": "AWS secret access key for ECR",
        "aws_session_token": "Optional AWS session token for temporary credentials",
        "region": "AWS region for ECR registry",
        "password": "Password for registry authentication",
        "registry_url": "URL for generic registry (optional)"
    }
    
    for cred_type, definition in CREDENTIAL_FIELD_DEFINITIONS.items():
        descriptions.append(CredentialTypeDescription(
            type=cred_type,
            name=cred_type.replace('_', ' ').title(),
            description=definition['description'],
            required_fields=definition['required'],
            optional_fields=definition['optional'],
            field_descriptions={
                field: field_descriptions.get(field, "")
                for field in definition['required'] + definition['optional']
            }
        ))
    
    return descriptions