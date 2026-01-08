"""
Encryption service for secure credential storage.

This service provides AES-256-GCM encryption for sensitive data like
SSH keys, access tokens, and other credentials. It uses a key derivation
function (PBKDF2) to generate encryption keys from a master key.

Author: Open WebUI Customizer Team
"""

import os
import base64
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag

from app.config.settings import get_settings
from app.exceptions import ConfigurationError, ValidationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EncryptionResult:
    """Container for encryption result data."""
    
    def __init__(
        self,
        ciphertext: bytes,
        nonce: bytes,
        tag: bytes,
        salt: bytes,
        key_id: str
    ):
        """
        Initialize encryption result.
        
        Args:
            ciphertext: Encrypted data
            nonce: Nonce used for encryption
            tag: Authentication tag
            salt: Salt used for key derivation
            key_id: Key identifier for rotation tracking
        """
        self.ciphertext = base64.b64encode(ciphertext).decode('utf-8')
        self.nonce = base64.b64encode(nonce).decode('utf-8')
        self.tag = base64.b64encode(tag).decode('utf-8')
        self.salt = base64.b64encode(salt).decode('utf-8')
        self.key_id = key_id
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            'ciphertext': self.ciphertext,
            'nonce': self.nonce,
            'tag': self.tag,
            'salt': self.salt,
            'key_id': self.key_id,
            'version': '1'
        }


class EncryptionService:
    """
    Handles encryption and decryption of sensitive data using AES-256-GCM.
    
    This service provides a secure way to store credentials and other sensitive
    information in the database. It uses a master key derived from environment
    variables and a PBKDF2-based key derivation function.
    
    Example:
        >>> service = EncryptionService()
        >>> encrypted = service.encrypt("sensitive data")
        >>> decrypted = service.decrypt(encrypted)
    """
    
    # Encryption constants
    ALGORITHM = 'AES-256-GCM'
    KEY_LENGTH = 32  # 256 bits
    SALT_LENGTH = 32  # 32 bytes for PBKDF2
    NONCE_LENGTH = 12  # 96 bits for GCM
    PBKDF2_ITERATIONS = 100000  # OWASP recommended
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize the encryption service.
        
        Args:
            master_key: Optional override for master key. If not provided,
                       will get from environment variables.
        
        Raises:
            ConfigurationError: If master key is not available.
        """
        self.master_key = master_key or self._get_master_key()
        self.current_key_id = self._generate_key_id()
        
        # Cache for derived keys to avoid re-computation
        self._key_cache: Dict[str, bytes] = {}
        self.cache_timeout = timedelta(hours=1)
        self._last_cache_clear = datetime.utcnow()
        
        logger.info("Encryption service initialized")
    
    def _get_master_key(self) -> str:
        """
        Retrieve master key from environment variables.
        
        Returns:
            Base64-encoded master key
            
        Raises:
            ConfigurationError: If master key is not configured and required.
        """
        settings = get_settings()
        
        # Check if encryption key is required for this environment
        require_key = getattr(settings.security, 'require_encryption_key', True)
        
        # Try multiple sources for the master key
        master_key = (
            os.environ.get('CREDENTIAL_MASTER_KEY') or
            getattr(settings.security, 'encryption_key', None) or
            getattr(settings.security, 'secret_key', None)
        )
        
        if not master_key:
            if require_key:
                raise ConfigurationError(
                    "CREDENTIAL_MASTER_KEY environment variable is required "
                    "for credential encryption in this environment. Generate one with: "
                    "openssl rand -base64 32"
                )
            else:
                # In development mode, use a default key if not required
                logger.warning("Using default encryption key for development - NOT FOR PRODUCTION")
                return "dev-default-encryption-key-32-bytes-long"
        
        # Validate key length (should be at least 32 bytes after base64 decode)
        try:
            decoded = base64.b64decode(master_key)
            if len(decoded) < 32:
                if require_key:
                    raise ConfigurationError(
                        "CREDENTIAL_MASTER_KEY must be at least 32 bytes after base64 decoding"
                    )
                else:
                    logger.warning("Encryption key is shorter than recommended")
        except Exception as e:
            if require_key:
                raise ConfigurationError(
                    f"Invalid CREDENTIAL_MASTER_KEY format: {str(e)}"
                )
            else:
                logger.warning(f"Invalid encryption key format, using default: {str(e)}")
                return "dev-default-encryption-key-32-bytes-long"
        
        return master_key
    
    def _generate_key_id(self) -> str:
        """
        Generate a unique key identifier for tracking key versions.
        
        Returns:
            String key identifier
        """
        # Use current timestamp and random bytes for uniqueness
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        random_bytes = secrets.token_bytes(4)
        return f"key_{timestamp}_{random_bytes.hex()}"
    
    def _derive_encryption_key(self, salt: bytes) -> bytes:
        """
        Derive encryption key from master key using PBKDF2.
        
        Args:
            salt: Salt for key derivation
            
        Returns:
            32-byte encryption key
        """
        salt_b64 = base64.b64encode(salt).decode('utf-8')
        
        # Check cache
        self._check_cache_timeout()
        if salt_b64 in self._key_cache:
            return self._key_cache[salt_b64]
        
        # Decode master key
        master_key_bytes = base64.b64decode(self.master_key)
        
        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        
        key = kdf.derive(master_key_bytes)
        
        # Cache the derived key
        self._key_cache[salt_b64] = key
        
        return key
    
    def _check_cache_timeout(self) -> None:
        """Clear key cache if it has expired."""
        if datetime.utcnow() - self._last_cache_clear > self.cache_timeout:
            self._key_cache.clear()
            self._last_cache_clear = datetime.utcnow()
    
    def encrypt(self, plaintext: str) -> Dict[str, str]:
        """
        Encrypt plaintext using AES-256-GCM.
        
        Args:
            plaintext: String data to encrypt
            
        Returns:
            Dictionary containing encrypted data and metadata
            
        Raises:
            ValidationError: If plaintext is empty or too large
        """
        if not plaintext:
            raise ValidationError("Cannot encrypt empty data")
        
        if len(plaintext) > 1024 * 1024:  # 1MB limit
            raise ValidationError("Data too large for encryption (max 1MB)")
        
        try:
            # Convert plaintext to bytes
            plaintext_bytes = plaintext.encode('utf-8')
            
            # Generate random salt and nonce
            salt = os.urandom(self.SALT_LENGTH)
            nonce = os.urandom(self.NONCE_LENGTH)
            
            # Derive encryption key
            key = self._derive_encryption_key(salt)
            
            # Encrypt with AES-GCM
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)
            
            # Split ciphertext and tag
            # In Python cryptography, tag is appended to ciphertext
            tag_length = 16  # GCM tag is 16 bytes
            actual_ciphertext = ciphertext[:-tag_length]
            tag = ciphertext[-tag_length:]
            
            # Create encryption result
            result = EncryptionResult(
                ciphertext=actual_ciphertext,
                nonce=nonce,
                tag=tag,
                salt=salt,
                key_id=self.current_key_id
            )
            
            logger.info("Successfully encrypted data", extra={
                'key_id': self.current_key_id,
                'data_length': len(plaintext_bytes)
            })
            
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise ValidationError(f"Encryption failed: {str(e)}")
    
    def decrypt(self, encrypted_data: Dict[str, str]) -> str:
        """
        Decrypt data that was encrypted with AES-256-GCM.
        
        Args:
            encrypted_data: Dictionary from encrypt() method
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            ValidationError: If decryption fails due to invalid data or tag
            NotFoundError: If data format is invalid
        """
        try:
            # Validate required fields
            required_fields = ['ciphertext', 'nonce', 'tag', 'salt', 'key_id']
            missing_fields = [f for f in required_fields if f not in encrypted_data]
            
            if missing_fields:
                raise ValidationError(f"Missing encryption fields: {missing_fields}")
            
            # Decode base64 components
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            nonce = base64.b64decode(encrypted_data['nonce'])
            tag = base64.b64decode(encrypted_data['tag'])
            salt = base64.b64decode(encrypted_data['salt'])
            
            # Derive decryption key
            key = self._derive_encryption_key(salt)
            
            # Reconstruct ciphertext with tag for AES-GCM
            full_ciphertext = ciphertext + tag
            
            # Decrypt
            aesgcm = AESGCM(key)
            plaintext_bytes = aesgcm.decrypt(nonce, full_ciphertext, None)
            
            # Convert to string
            plaintext = plaintext_bytes.decode('utf-8')
            
            logger.info("Successfully decrypted data", extra={
                'key_id': encrypted_data.get('key_id'),
                'data_length': len(plaintext_bytes)
            })
            
            return plaintext
            
        except InvalidTag as e:
            logger.error(f"Decryption failed: Invalid authentication tag - {str(e)}")
            raise ValidationError("Decryption failed: invalid authentication tag. "
                                "Data may be corrupted or tampered with.")
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise ValidationError(f"Decryption failed: {str(e)}")
    
    def generate_secure_random(self, length: int = 32) -> str:
        """
        Generate a cryptographically secure random string.
        
        Args:
            length: Number of random bytes to generate
            
        Returns:
            Base64-encoded random string
        """
        random_bytes = secrets.token_bytes(length)
        return base64.b64encode(random_bytes).decode('utf-8')
    
    def rotate_key(self) -> str:
        """
        Rotate the current encryption key.
        
        Returns:
            New key ID
        """
        self.current_key_id = self._generate_key_id()
        self._key_cache.clear()
        
        logger.info(f"Encryption key rotated to {self.current_key_id}")
        
        return self.current_key_id
    
    def validate_encryption_integrity(self, encrypted_data: Dict[str, str]) -> bool:
        """
        Validate the integrity of encrypted data without decrypting.
        
        Args:
            encrypted_data: Dictionary containing encrypted data
            
        Returns:
            True if data format is valid, False otherwise
        """
        try:
            required_fields = ['ciphertext', 'nonce', 'tag', 'salt', 'key_id']
            if not all(f in encrypted_data for f in required_fields):
                return False
            
            # Try to decode base64 components
            base64.b64decode(encrypted_data['ciphertext'])
            base64.b64decode(encrypted_data['nonce'])
            base64.b64decode(encrypted_data['tag'])
            base64.b64decode(encrypted_data['salt'])
            
            return True
        except Exception:
            return False


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get the singleton encryption service instance.
    
    Returns:
        Global encryption service instance
        
    Raises:
        ConfigurationError: If master key is not configured
    """
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    
    return _encryption_service


def rotate_encryption_key() -> Tuple[str, str]:
    """
    Rotate the global encryption key.
    
    Returns:
        Tuple of (old_key_id, new_key_id)
    
    Raises:
        ConfigurationError: If encryption service is not initialized
    """
    service = get_encryption_service()
    old_key_id = service.current_key_id
    new_key_id = service.rotate_key()
    
    return old_key_id, new_key_id