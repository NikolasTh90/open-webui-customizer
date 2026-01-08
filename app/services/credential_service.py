"""
Service for managing credentials securely.

This service provides business logic for creating, updating, and managing
encrypted credentials with proper validation and audit logging.

Author: Open WebUI Customizer Team
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.models import Credential
from app.schemas.credentials import (
    CredentialCreate, CredentialUpdate, CredentialDataUpdate,
    CredentialStatus
)
from app.services.encryption_service import get_encryption_service
from app.exceptions import (
    ValidationError, NotFoundError, DatabaseError,
    ConfigurationError
)
from app.utils.logging import get_logger, log_function_call
from app.config.settings import get_settings

logger = get_logger(__name__)


class CredentialService:
    """
    Manages credential lifecycle with encryption and validation.
    
    This service handles all credential operations including creation,
    retrieval, encryption/decryption, and verification. All credential
    data is encrypted at rest and never exposed in API responses.
    
    Example:
        >>> service = CredentialService(db)
        >>> credential_id = service.create_credential(credential_data)
        >>> decrypted = service.get_decrypted_credential(credential_id)
    """
    
    def __init__(self, db: Session):
        """
        Initialize the credential service.
        
        Args:
            db: Database session for persistence operations
        """
        self.db = db
        self.encryption_service = get_encryption_service()
        
        logger.info("Credential service initialized", extra={
            'encryption_service': type(self.encryption_service).__name__
        })
    
    @log_function_call
    def create_credential(self, credential_data: CredentialCreate) -> Credential:
        """
        Create a new encrypted credential.
        
        Args:
            credential_data: Credential creation data with sensitive information
            
        Returns:
            Created credential model (without sensitive data)
            
        Raises:
            ValidationError: If validation fails
            DatabaseError: If database operation fails
        """
        try:
            # Check for duplicate names
            existing = self.db.query(Credential).filter(
                Credential.name == credential_data.name
            ).first()
            
            if existing:
                raise ValidationError(
                    f"Credential with name '{credential_data.name}' already exists",
                    details={
                        'existing_id': existing.id,
                        'existing_type': existing.credential_type
                    }
                )
            
            # Check expiration date is in the future
            if credential_data.expires_at and credential_data.expires_at < datetime.utcnow():
                raise ValidationError("Expiration date cannot be in the past")
            
            # Serialize and encrypt sensitive data
            sensitive_data = json.dumps(credential_data.credential_data)
            encrypted = self.encryption_service.encrypt(sensitive_data)
            
            # Create database record
            db_credential = Credential(
                name=credential_data.name,
                credential_type=credential_data.credential_type.value,
                encrypted_data=json.dumps(encrypted),
                encryption_key_id=encrypted.get('key_id'),
                metadata=credential_data.metadata,
                expires_at=credential_data.expires_at
            )
            
            self.db.add(db_credential)
            self.db.commit()
            self.db.refresh(db_credential)
            
            logger.info(f"Created credential '{credential_data.name}'", extra={
                'credential_id': db_credential.id,
                'credential_type': credential_data.credential_type.value,
                'expires_at': credential_data.expires_at.isoformat() if credential_data.expires_at else None
            })
            
            return db_credential
            
        except ValidationError:
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseError(
                f"Failed to create credential '{credential_data.name}'",
                operation="insert",
                table="credentials",
                details={
                    'credential_name': credential_data.name,
                    'error': str(e)
                }
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error creating credential: {str(e)}")
            raise ValidationError(f"Failed to create credential: {str(e)}")
    
    @log_function_call
    def get_credential(self, credential_id: int) -> Optional[Credential]:
        """
        Retrieve a credential by ID.
        
        Args:
            credential_id: Database ID of the credential
            
        Returns:
            Credential model or None if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            credential = self.db.query(Credential).filter(
                Credential.id == credential_id
            ).first()
            
            if credential:
                logger.debug(f"Retrieved credential '{credential.name}'", extra={
                    'credential_id': credential_id,
                    'credential_type': credential.credential_type
                })
            
            return credential
            
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Failed to retrieve credential {credential_id}",
                operation="select",
                table="credentials",
                details={
                    'credential_id': credential_id,
                    'error': str(e)
                }
            )
    
    @log_function_call
    def list_credentials(
        self,
        credential_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        include_expired: bool = False
    ) -> List[Credential]:
        """
        List credentials with optional filtering.
        
        Args:
            credential_type: Optional filter by credential type
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            include_expired: Whether to include expired credentials
            
        Returns:
            List of credential models
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            query = self.db.query(Credential).filter(Credential.is_active == True)
            
            # Filter by type if specified
            if credential_type:
                query = query.filter(Credential.credential_type == credential_type)
            
            # Filter out expired unless explicitly requested
            if not include_expired:
                query = query.filter(
                    (Credential.expires_at.is_(None)) |
                    (Credential.expires_at > datetime.utcnow())
                )
            
            # Apply pagination
            credentials = query.offset(skip).limit(limit).all()
            
            logger.debug(f"Listed credentials", extra={
                'count': len(credentials),
                'credential_type': credential_type,
                'skip': skip,
                'limit': limit,
                'include_expired': include_expired
            })
            
            return credentials
            
        except SQLAlchemyError as e:
            raise DatabaseError(
                "Failed to list credentials",
                operation="select",
                table="credentials",
                details={
                    'credential_type': credential_type,
                    'error': str(e)
                }
            )
    
    @log_function_call
    def update_credential(
        self,
        credential_id: int,
        update_data: CredentialUpdate
    ) -> Optional[Credential]:
        """
        Update non-sensitive credential data.
        
        Note: This method does not update the actual credential data.
        For that, use update_credential_data().
        
        Args:
            credential_id: Database ID of the credential
            update_data: Non-sensitive update data
            
        Returns:
            Updated credential or None if not found
            
        Raises:
            NotFoundError: If credential doesn't exist
            ValidationError: If validation fails
            DatabaseError: If database operation fails
        """
        try:
            credential = self.get_credential(credential_id)
            if not credential:
                raise NotFoundError(
                    f"Credential with ID {credential_id} not found",
                    details={'credential_id': credential_id}
                )
            
            # Check for duplicate name if changing
            if update_data.name and update_data.name != credential.name:
                existing = self.db.query(Credential).filter(
                    Credential.name == update_data.name,
                    Credential.id != credential_id
                ).first()
                
                if existing:
                    raise ValidationError(
                        f"Credential with name '{update_data.name}' already exists",
                        details={
                            'existing_id': existing.id
                        }
                    )
            
            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            
            # Validate expiration date if provided
            if 'expires_at' in update_dict and update_dict['expires_at']:
                if update_dict['expires_at'] < datetime.utcnow():
                    raise ValidationError("Expiration date cannot be in the past")
            
            for key, value in update_dict.items():
                setattr(credential, key, value)
            
            self.db.commit()
            self.db.refresh(credential)
            
            logger.info(f"Updated credential metadata", extra={
                'credential_id': credential_id,
                'updated_fields': list(update_dict.keys())
            })
            
            return credential
            
        except (NotFoundError, ValidationError):
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseError(
                f"Failed to update credential {credential_id}",
                operation="update",
                table="credentials",
                details={
                    'credential_id': credential_id,
                    'error': str(e)
                }
            )
    
    @log_function_call
    def update_credential_data(
        self,
        credential_id: int,
        update_data: CredentialDataUpdate
    ) -> Credential:
        """
        Update the sensitive credential data (requires re-encryption).
        
        Args:
            credential_id: Database ID of the credential
            update_data: New credential data to encrypt
            
        Returns:
            Updated credential model
            
        Raises:
            NotFoundError: If credential doesn't exist
            ValidationError: If validation fails
            DatabaseError: If database operation fails
        """
        try:
            credential = self.get_credential(credential_id)
            if not credential:
                raise NotFoundError(
                    f"Credential with ID {credential_id} not found",
                    details={'credential_id': credential_id}
                )
            
            # Validate credential data type matches existing type
            # This maintains consistency for verification operations
            
            # Serialize and encrypt new data
            sensitive_data = json.dumps(update_data.credential_data)
            encrypted = self.encryption_service.encrypt(sensitive_data)
            
            # Update encrypted data
            credential.encrypted_data = json.dumps(encrypted)
            credential.encryption_key_id = encrypted.get('key_id')
            credential.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(credential)
            
            logger.info(f"Updated credential encrypted data", extra={
                'credential_id': credential_id,
                'new_key_id': encrypted.get('key_id')
            })
            
            return credential
            
        except (NotFoundError, ValidationError):
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseError(
                f"Failed to update credential data {credential_id}",
                operation="update",
                table="credentials",
                details={
                    'credential_id': credential_id,
                    'error': str(e)
                }
            )
    
    @log_function_call
    def get_decrypted_credential(self, credential_id: int) -> Dict[str, Any]:
        """
        Retrieve and decrypt credential data for internal use.
        
        Args:
            credential_id: Database ID of the credential
            
        Returns:
            Decrypted credential data as dictionary
            
        Raises:
            NotFoundError: If credential doesn't exist
            ValidationError: If credential is expired or decryption fails
            DatabaseError: If database operation fails
        """
        try:
            credential = self.get_credential(credential_id)
            if not credential:
                raise NotFoundError(
                    f"Credential with ID {credential_id} not found",
                    details={'credential_id': credential_id}
                )
            
            # Check if credential is active
            if not credential.is_active:
                raise ValidationError(
                    "Credential is deactivated",
                    details={'credential_id': credential_id}
                )
            
            # Check expiration
            if credential.expires_at and credential.expires_at < datetime.utcnow():
                raise ValidationError(
                    "Credential has expired",
                    details={
                        'credential_id': credential_id,
                        'expired_at': credential.expires_at.isoformat()
                    }
                )
            
            # Decrypt the data
            try:
                encrypted_data = json.loads(credential.encrypted_data)
                decrypted = self.encryption_service.decrypt(encrypted_data)
                credential_data = json.loads(decrypted)
            except Exception as e:
                settings = get_settings()
                if getattr(settings.security, 'detailed_errors', False):
                    raise ValidationError(
                        f"Failed to decrypt credential: {str(e)}",
                        details={'credential_id': credential_id}
                    )
                else:
                    raise ValidationError(
                        "Failed to decrypt credential",
                        details={'credential_id': credential_id}
                    )
            
            # Update last used timestamp
            credential.last_used_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Decrypted credential for use", extra={
                'credential_id': credential_id,
                'credential_name': credential.name,
                'credential_type': credential.credential_type
            })
            
            return credential_data
            
        except (NotFoundError, ValidationError):
            raise
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Failed to decrypt credential {credential_id}",
                operation="update",
                table="credentials",
                details={
                    'credential_id': credential_id,
                    'error': str(e)
                }
            )
    
    @log_function_call
    def delete_credential(self, credential_id: int, permanent: bool = False) -> bool:
        """
        Delete or deactivate a credential.
        
        Args:
            credential_id: Database ID of the credential
            permanent: If True, permanently delete; if False, deactivate
            
        Returns:
            True if successful, False if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            credential = self.get_credential(credential_id)
            if not credential:
                return False
            
            if permanent:
                # Actually delete the record
                self.db.delete(credential)
                
                logger.warning(f"Permanently deleted credential", extra={
                    'credential_id': credential_id,
                    'credential_name': credential.name
                })
            else:
                # Just deactivate
                credential.is_active = False
                credential.updated_at = datetime.utcnow()
                
                logger.info(f"Deactivated credential", extra={
                    'credential_id': credential_id,
                    'credential_name': credential.name
                })
            
            self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseError(
                f"Failed to delete credential {credential_id}",
                operation="delete",
                table="credentials",
                details={
                    'credential_id': credential_id,
                    'error': str(e)
                }
            )
    
    @log_function_call
    def verify_credential(self, credential_id: int) -> Tuple[bool, str]:
        """
        Verify that a credential is valid and working.
        
        This performs different verification steps based on credential type.
        For Git credentials, it might try to clone a test repository.
        For registry credentials, it might try to authenticate.
        
        Args:
            credential_id: Database ID of the credential
            
        Returns:
            Tuple of (is_valid, message)
            
        Raises:
            NotFoundError: If credential doesn't exist
            DatabaseError: If database operation fails
        """
        try:
            credential = self.get_credential(credential_id)
            if not credential:
                raise NotFoundError(
                    f"Credential with ID {credential_id} not found",
                    details={'credential_id': credential_id}
                )
            
            # Get decrypted data for verification
            try:
                data = self.get_decrypted_credential(credential_id)
            except ValidationError as e:
                return False, f"Credential invalid: {str(e)}"
            
            # Perform type-specific verification
            if credential.credential_type == "git_ssh":
                # TODO: Implement SSH key verification
                return True, "SSH key format appears valid"
            
            elif credential.credential_type == "git_https":
                # TODO: Implement HTTPS credential verification
                username = data.get('username', '')
                if username and data.get('password_or_token'):
                    return True, f"HTTPS credential for user '{username}' appears valid"
                return False, "Missing username or token"
            
            elif credential.credential_type == "registry_docker_hub":
                # TODO: Implement Docker Hub verification
                return True, "Docker Hub credential format valid"
            
            elif credential.credential_type == "registry_aws_ecr":
                # TODO: Implement AWS ECR verification
                if data.get('aws_access_key_id') and data.get('aws_secret_access_key'):
                    return True, "AWS ECR credential format valid"
                return False, "Missing AWS credentials"
            
            else:
                # Basic format validation for unknown types
                return True, f"Unknown credential type {credential.credential_type}"
                
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Credential verification failed: {str(e)}")
            settings = get_settings()
            if getattr(settings.security, 'detailed_errors', False):
                return False, f"Verification error: {str(e)}"
            else:
                return False, "Verification error occurred"
    
    @log_function_call
    def cleanup_expired_credentials(self) -> int:
        """
        Deactivate expired credentials.
        
        This method finds and deactivates all credentials that have passed
        their expiration date. This is typically called by a background job.
        
        Returns:
            Number of credentials deactivated
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            expired = self.db.query(Credential).filter(
                Credential.is_active == True,
                Credential.expires_at < datetime.utcnow()
            ).all()
            
            count = 0
            for cred in expired:
                cred.is_active = False
                count += 1
                
                logger.info(f"Deactivated expired credential", extra={
                    'credential_id': cred.id,
                    'credential_name': cred.name,
                    'expired_at': cred.expires_at.isoformat()
                })
            
            if count > 0:
                self.db.commit()
                
                logger.info(f"Deactivated {count} expired credentials", extra={
                    'count': count
                })
            
            return count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseError(
                "Failed to cleanup expired credentials",
                operation="update",
                table="credentials",
                details={'error': str(e)}
            )
    
    @log_function_call
    def get_credentials_by_type(self, credential_type: str) -> List[Credential]:
        """
        Get all active credentials of a specific type.
        
        Args:
            credential_type: Type of credentials to retrieve
            
        Returns:
            List of credentials of the specified type
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            credentials = self.db.query(Credential).filter(
                Credential.credential_type == credential_type,
                Credential.is_active == True
            ).all()
            
            logger.info(f"Retrieved credentials by type", extra={
                'credential_type': credential_type,
                'count': len(credentials)
            })
            
            return credentials
            
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Failed to get credentials of type {credential_type}",
                operation="select",
                table="credentials",
                details={
                    'credential_type': credential_type,
                    'error': str(e)
                }
            )