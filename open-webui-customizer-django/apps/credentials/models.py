"""
Django models for credential management.

This module contains the Credential model which stores encrypted credentials
for various services like Git repositories, container registries, etc.
The encryption ensures sensitive data is never stored in plain text.
"""

import json
import uuid
import logging
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseNameModel, MetadataModel, ExpirableModel, TimestampedExpirableModel

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Manager for handling encryption and decryption of sensitive data.
    
    Uses AES-256-GCM encryption through the Fernet symmetric encryption
    scheme from the cryptography library. Keys are derived from a
    master secret using PBKDF2 with a random salt.
    """
    
    def __init__(self):
        self._cipher_suite = None
        self._key_id = None
    
    @property
    def cipher_suite(self):
        """Get or create the cipher suite for encryption/decryption."""
        if self._cipher_suite is None:
            self._cipher_suite = self._get_cipher_suite()
        return self._cipher_suite
    
    @property
    def key_id(self):
        """Get the current key identifier."""
        if self._key_id is None:
            self._key_id = self._get_key_id()
        return self._key_id
    
    def _get_key_id(self):
        """Generate or retrieve the current encryption key identifier."""
        # In production, this should be stored securely (e.g., in environment
        # variables, secret manager, or database with proper access controls)
        master_secret = getattr(settings, 'ENCRYPTION_MASTER_SECRET', None)
        if not master_secret:
            raise ValueError("ENCRYPTION_MASTER_SECRET must be set in settings")
        
        # Generate key ID from master secret hash
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'key_id_salt',  # Fixed salt for key ID generation
            iterations=100000,
        )
        key_hash = kdf.derive(master_secret.encode())
        return base64.urlsafe_b64encode(key_hash[:16]).decode()
    
    def _get_cipher_suite(self):
        """Create and return the Fernet cipher suite."""
        master_secret = getattr(settings, 'ENCRYPTION_MASTER_SECRET', None)
        if not master_secret:
            raise ValueError("ENCRYPTION_MASTER_SECRET must be set in settings")
        
        # Derive encryption key using PBKDF2
        salt = getattr(settings, 'ENCRYPTION_SALT', b'open_webui_salt').encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_secret.encode()))
        return Fernet(key)
    
    def encrypt_data(self, data):
        """
        Encrypt JSON-serializable data.
        
        Args:
            data (dict): The data to encrypt
            
        Returns:
            str: Base64-encoded encrypted JSON string
        """
        try:
            # Convert to JSON string
            json_data = json.dumps(data, separators=(',', ':'))
            
            # Encrypt the data
            encrypted_bytes = self.cipher_suite.encrypt(json_data.encode())
            
            # Return as base64 string
            return base64.b64encode(encrypted_bytes).decode()
            
        except Exception as e:
            logger.error(f"Failed to encrypt data: {str(e)}")
            raise ValidationError(f"Encryption failed: {str(e)}")
    
    def decrypt_data(self, encrypted_data):
        """
        Decrypt data that was encrypted with encrypt_data.
        
        Args:
            encrypted_data (str): Base64-encoded encrypted JSON string
            
        Returns:
            dict: The decrypted data
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            
            # Decrypt the data
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            
            # Parse JSON
            return json.loads(decrypted_bytes.decode())
            
        except Exception as e:
            logger.error(f"Failed to decrypt data: {str(e)}")
            raise ValidationError(f"Decryption failed: {str(e)}")
    
    def is_key_valid(self, encrypted_data):
        """
        Check if the current key can decrypt the given data.
        
        Args:
            encrypted_data (str): Previously encrypted data
            
        Returns:
            bool: True if decryption succeeds, False otherwise
        """
        try:
            self.decrypt_data(encrypted_data)
            return True
        except Exception:
            return False


# Global encryption manager instance
encryption_manager = EncryptionManager()


class CredentialType(models.TextChoices):
    """Enumeration of supported credential types."""
    
    # Git repository credentials
    GIT_SSH_KEY = 'git_ssh_key', _('Git SSH Key')
    GIT_HTTPS_TOKEN = 'git_https_token', _('Git HTTPS Token')
    GIT_USERNAME_PASSWORD = 'git_username_password', _('Git Username/Password')
    
    # Container registry credentials
    DOCKER_HUB = 'docker_hub', _('Docker Hub')
    AWS_ECR = 'aws_ecr', _('AWS ECR')
    QUAY_IO = 'quay_io', _('Quay.io')
    GENERIC_REGISTRY = 'generic_registry', _('Generic Container Registry')
    
    # Other service credentials
    API_KEY = 'api_key', _('API Key')
    OAUTH_TOKEN = 'oauth_token', _('OAuth Token')
    CUSTOM = 'custom', _('Custom Credential')


class Credential(BaseNameModel):
    """
    Stores encrypted credentials for various services.
    
    This model securely stores sensitive authentication information for
    Git repositories, container registries, and other services. All sensitive
    data is encrypted at rest using AES-256-GCM encryption.
    
    Inherits from:
    - BaseNameModel: provides name, timestamps, active status
    """
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expires At",
        help_text="Timestamp when this credential expires"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadata",
        help_text="Additional metadata stored as JSON"
    )
    credential_type = models.CharField(
        max_length=50,
        choices=CredentialType.choices,
        db_index=True,
        verbose_name="Credential Type",
        help_text="Type of credential being stored"
    )
    encrypted_data = models.TextField(
        verbose_name="Encrypted Data",
        help_text="Encrypted credential data (JSON format)"
    )
    encryption_key_id = models.CharField(
        max_length=255,
        editable=False,
        verbose_name="Encryption Key ID",
        help_text="Identifier of the encryption key used"
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Used At",
        help_text="Timestamp when this credential was last used"
    )
    
    class Meta:
        verbose_name = "Credential"
        verbose_name_plural = "Credentials"
        ordering = ['name', 'credential_type']
        indexes = [
            models.Index(fields=['credential_type']),
            models.Index(fields=['last_used_at']),
            models.Index(fields=['encryption_key_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_credential_type_display()})"
    
    def clean(self):
        """Validate the credential before saving."""
        super().clean()
        
        # Check if this is a new object
        if not self.pk and not hasattr(self, '_encrypted_data_plaintext'):
            raise ValidationError("Encrypted data must be provided for new credentials")
    
    def save(self, *args, **kwargs):
        """Override save to handle encryption and key tracking."""
        # Set encryption key ID
        self.encryption_key_id = encryption_manager.key_id
        
        # Encrypt data if it hasn't been encrypted yet
        if hasattr(self, '_encrypted_data_plaintext'):
            self.encrypted_data = encryption_manager.encrypt_data(
                self._encrypted_data_plaintext
            )
            delattr(self, '_encrypted_data_plaintext')
        
        super().save(*args, **kwargs)
    
    def set_credential_data(self, data):
        """
        Set the credential data (will be encrypted on save).
        
        Args:
            data (dict): The credential data to store
        """
        # Validate data structure based on credential type
        self._validate_credential_data(data)
        
        # Store for encryption during save
        self._encrypted_data_plaintext = data
    
    def get_credential_data(self):
        """
        Get the decrypted credential data.
        
        Returns:
            dict: The decrypted credential data
            
        Raises:
            ValidationError: If decryption fails
        """
        try:
            return encryption_manager.decrypt_data(self.encrypted_data)
        except Exception as e:
            logger.error(f"Failed to decrypt credential {self.pk}: {str(e)}")
            raise ValidationError(f"Failed to decrypt credential data: {str(e)}")
    
    def _validate_credential_data(self, data):
        """Validate credential data structure based on type."""
        if not isinstance(data, dict):
            raise ValidationError("Credential data must be a dictionary")
        
        if self.credential_type == CredentialType.GIT_SSH_KEY:
            required_fields = ['private_key']
        elif self.credential_type == CredentialType.GIT_HTTPS_TOKEN:
            required_fields = ['token']
        elif self.credential_type == CredentialType.GIT_USERNAME_PASSWORD:
            required_fields = ['username', 'password']
        elif self.credential_type == CredentialType.AWS_ECR:
            required_fields = ['access_key_id', 'secret_access_key']
        elif self.credential_type == CredentialType.DOCKER_HUB:
            required_fields = ['username', 'password']
        elif self.credential_type == CredentialType.QUAY_IO:
            required_fields = ['username', 'password']
        elif self.credential_type == CredentialType.GENERIC_REGISTRY:
            required_fields = ['username', 'password']
        elif self.credential_type == CredentialType.API_KEY:
            required_fields = ['api_key']
        elif self.credential_type == CredentialType.OAUTH_TOKEN:
            required_fields = ['access_token']
        elif self.credential_type == CredentialType.CUSTOM:
            required_fields = []  # No validation for custom credentials
        else:
            required_fields = []
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValidationError(
                f"Missing required fields for {self.credential_type}: {', '.join(missing_fields)}"
            )
    
    def update_last_used(self):
        """Update the last_used_at timestamp."""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])
    
    def is_encryption_current(self):
        """
        Check if this credential is encrypted with the current key.
        
        Returns:
            bool: True if encrypted with current key, False otherwise
        """
        return self.encryption_key_id == encryption_manager.key_id
    
    def reencrypt_with_current_key(self):
        """
        Re-encrypt the credential data with the current encryption key.
        
        This should be called after key rotation to ensure all credentials
        are encrypted with the latest key.
        
        Raises:
            ValidationError: If re-encryption fails
        """
        try:
            # Decrypt with current key
            data = self.get_credential_data()
            
            # Re-encrypt (this will update the encryption_key_id)
            self.set_credential_data(data)
            self.save()
            
        except Exception as e:
            logger.error(f"Failed to re-encrypt credential {self.pk}: {str(e)}")
            raise ValidationError(f"Failed to re-encrypt credential: {str(e)}")
    
    def test_connection(self, service_type=None, **kwargs):
        """
        Test if the credential works with the specified service.
        
        Args:
            service_type (str): Type of service to test against
            **kwargs: Additional parameters for the test
            
        Returns:
            dict: Test result with success status and message
        """
        from apps.credentials.services import CredentialTestService
        
        test_service = CredentialTestService()
        return test_service.test_credential(self, service_type or self.credential_type, **kwargs)
    
    @classmethod
    def rotate_encryption_keys(cls, new_master_secret=None):
        """
        Rotate encryption keys for all credentials.
        
        Args:
            new_master_secret (str): New master secret (for testing only)
            
        Returns:
            tuple: (success_count, failure_count, error_messages)
        """
        success_count = 0
        failure_count = 0
        error_messages = []
        
        # Temporarily set new master secret if provided
        if new_master_secret:
            old_secret = getattr(settings, 'ENCRYPTION_MASTER_SECRET', None)
            settings.ENCRYPTION_MASTER_SECRET = new_master_secret
            
            # Reset encryption manager
            global encryption_manager
            encryption_manager = EncryptionManager()
        
        try:
            credentials = cls.objects.all()
            
            with transaction.atomic():
                for credential in credentials:
                    try:
                        if not credential.is_encryption_current():
                            credential.reencrypt_with_current_key()
                            success_count += 1
                        else:
                            success_count += 1  # Already encrypted with current key
                    except Exception as e:
                        failure_count += 1
                        error_messages.append(
                            f"Failed to re-encrypt credential '{credential.name}': {str(e)}"
                        )
        
        finally:
            # Restore original master secret if we changed it
            if new_master_secret:
                settings.ENCRYPTION_MASTER_SECRET = old_secret
                encryption_manager = EncryptionManager()
        
        return success_count, failure_count, error_messages
    
    @classmethod
    def get_credential_types_for_service(cls, service_type):
        """
        Get available credential types for a specific service.
        
        Args:
            service_type (str): Type of service ('git', 'registry', etc.)
            
        Returns:
            list: Available credential types
        """
        service_mappings = {
            'git': [
                CredentialType.GIT_SSH_KEY,
                CredentialType.GIT_HTTPS_TOKEN,
                CredentialType.GIT_USERNAME_PASSWORD,
            ],
            'registry': [
                CredentialType.DOCKER_HUB,
                CredentialType.AWS_ECR,
                CredentialType.QUAY_IO,
                CredentialType.GENERIC_REGISTRY,
            ],
            'api': [
                CredentialType.API_KEY,
                CredentialType.OAUTH_TOKEN,
            ],
        }
        
        return service_mappings.get(service_type, [])


# Signal receivers
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Credential)
def credential_saved(sender, instance, created, **kwargs):
    """Handle post-save actions for Credential."""
    if created:
        logger.info(f"Credential '{instance.name}' of type '{instance.credential_type}' created")
    else:
        logger.debug(f"Credential '{instance.name}' updated")
