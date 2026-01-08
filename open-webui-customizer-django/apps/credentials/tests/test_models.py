"""
Tests for credentials app models.
"""

import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from unittest.mock import patch, MagicMock
from apps.credentials.models import Credential, CredentialType
from apps.core.tests.factories import CredentialFactory


class CredentialTest(TestCase):
    """Test cases for Credential model."""
    
    def setUp(self):
        """Set up test data."""
        self.credential = CredentialFactory()
    
    def test_credential_creation(self):
        """Test Credential creation."""
        self.assertTrue(isinstance(self.credential, Credential))
        self.assertEqual(str(self.credential), f"{self.credential.name} ({self.credential.get_credential_type_display()})")
    
    def test_credential_fields(self):
        """Test Credential fields."""
        credential = Credential.objects.create(
            name="Test Credential",
            description="Test description",
            credential_type=CredentialType.GIT_TOKEN,
            encrypted_data={"token": "test_token"},
            is_active=True
        )
        
        self.assertEqual(credential.name, "Test Credential")
        self.assertEqual(credential.credential_type, CredentialType.GIT_TOKEN)
        self.assertTrue(credential.is_active)
    
    def test_credential_types(self):
        """Test all credential types."""
        types = [
            CredentialType.GIT_SSH_KEY,
            CredentialType.GIT_TOKEN,
            CredentialType.DOCKER_REGISTRY,
            CredentialType.AWS_ECR
        ]
        
        for cred_type in types:
            credential = CredentialFactory(credential_type=cred_type)
            self.assertEqual(credential.credential_type, cred_type)
    
    def test_encrypt_decrypt_data(self):
        """Test data encryption and decryption."""
        test_data = {"secret": "test_value"}
        credential = CredentialFactory()
        
        # Test encryption
        credential.encrypted_data = test_data
        credential.save()
        
        # Test decryption
        credential.refresh_from_db()
        self.assertEqual(credential.encrypted_data, test_data)
    
    def test_validate_credential_data_git_ssh_key(self):
        """Test validation for Git SSH key credentials."""
        # Valid SSH key data
        valid_data = {
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
            "public_key": "ssh-rsa abc123 test@example.com"
        }
        credential = CredentialFactory(credential_type=CredentialType.GIT_SSH_KEY)
        credential.validate_credential_data(valid_data)
        
        # Invalid SSH key data - missing fields
        invalid_data = {"private_key": "test"}
        with self.assertRaises(ValidationError):
            credential.validate_credential_data(invalid_data)
    
    def test_validate_credential_data_git_token(self):
        """Test validation for Git token credentials."""
        # Valid token data
        valid_data = {"token": "ghp_" + "x" * 40}
        credential = CredentialFactory(credential_type=CredentialType.GIT_TOKEN)
        credential.validate_credential_data(valid_data)
        
        # Invalid token data - missing token
        invalid_data = {"password": "test"}
        with self.assertRaises(ValidationError):
            credential.validate_credential_data(invalid_data)
    
    def test_validate_credential_data_docker_registry(self):
        """Test validation for Docker registry credentials."""
        # Valid registry data
        valid_data = {
            "username": "testuser",
            "password": "testpass"
        }
        credential = CredentialFactory(credential_type=CredentialType.DOCKER_REGISTRY)
        credential.validate_credential_data(valid_data)
        
        # Invalid registry data - missing username
        invalid_data = {"password": "testpass"}
        with self.assertRaises(ValidationError):
            credential.validate_credential_data(invalid_data)
    
    def test_validate_credential_data_aws_ecr(self):
        """Test validation for AWS ECR credentials."""
        # Valid ECR data
        valid_data = {
            "access_key_id": "AKIA" + "X" * 16,
            "secret_access_key": "x" * 40,
            "region": "us-east-1"
        }
        credential = CredentialFactory(credential_type=CredentialType.AWS_ECR)
        credential.validate_credential_data(valid_data)
        
        # Invalid ECR data - missing fields
        invalid_data = {"access_key_id": "test"}
        with self.assertRaises(ValidationError):
            credential.validate_credential_data(invalid_data)
    
    def test_mask_sensitive_data(self):
        """Test masking of sensitive data in string representation."""
        credential = CredentialFactory(
            name="My Secret Credential",
            credential_type=CredentialType.GIT_TOKEN
        )
        
        string_repr = str(credential)
        self.assertIn("My Secret Credential", string_repr)
        self.assertIn("Git Token", string_repr)
    
    def test_queryset_active(self):
        """Test custom queryset for active credentials."""
        active_credential = CredentialFactory(is_active=True)
        inactive_credential = CredentialFactory(is_active=False)
        
        active_credentials = Credential.objects.active()
        self.assertIn(active_credential, active_credentials)
        self.assertNotIn(inactive_credential, active_credentials)
    
    def test_queryset_by_credential_type(self):
        """Test filtering by credential type."""
        git_credential = CredentialFactory(credential_type=CredentialType.GIT_TOKEN)
        docker_credential = CredentialFactory(credential_type=CredentialType.DOCKER_REGISTRY)
        
        git_credentials = Credential.objects.by_credential_type(CredentialType.GIT_TOKEN)
        self.assertIn(git_credential, git_credentials)
        self.assertNotIn(docker_credential, git_credentials)
    
    def test_rotation_required_property(self):
        """Test rotation_required property."""
        # Old credential should require rotation
        old_credential = self.credential
        old_credential.created_at = timezone.now() - timezone.timedelta(days=400)
        old_credential.save()
        
        self.assertTrue(old_credential.rotation_required)
        
        # New credential should not require rotation
        new_credential = CredentialFactory()
        self.assertFalse(new_credential.rotation_required)
    
    @patch('apps.credentials.models.encrypt_data')
    @patch('apps.credentials.models.decrypt_data')
    def test_encryption_methods(self, mock_decrypt, mock_encrypt):
        """Test encryption/decryption methods."""
        test_data = {"secret": "value"}
        
        # Test encrypt_data
        mock_encrypt.return_value = "encrypted_value"
        credential = CredentialFactory()
        credential.encrypted_data = test_data
        self.assertTrue(mock_encrypt.called)
        
        # Test decrypt_data when accessing
        mock_decrypt.return_value = test_data
        credential.refresh_from_db()
        self.assertEqual(credential.encrypted_data, test_data)
        self.assertTrue(mock_decrypt.called)
    
    def test_get_git_credentials(self):
        """Test getting Git-specific credentials."""
        git_ssh = CredentialFactory(credential_type=CredentialType.GIT_SSH_KEY)
        git_token = CredentialFactory(credential_type=CredentialType.GIT_TOKEN)
        docker = CredentialFactory(credential_type=CredentialType.DOCKER_REGISTRY)
        
        git_credentials = Credential.objects.get_git_credentials()
        self.assertIn(git_ssh, git_credentials)
        self.assertIn(git_token, git_credentials)
        self.assertNotIn(docker, git_credentials)
    
    def test_get_registry_credentials(self):
        """Test getting registry credentials."""
        docker = CredentialFactory(credential_type=CredentialType.DOCKER_REGISTRY)
        ecr = CredentialFactory(credential_type=CredentialType.AWS_ECR)
        git = CredentialFactory(credential_type=CredentialType.GIT_TOKEN)
        
        registry_credentials = Credential.objects.get_registry_credentials()
        self.assertIn(docker, registry_credentials)
        self.assertIn(ecr, registry_credentials)
        self.assertNotIn(git, registry_credentials)
    
    def test_soft_delete(self):
        """Test soft delete functionality."""
        credential = CredentialFactory(is_active=True)
        
        # Soft delete
        credential.soft_delete()
        
        credential.refresh_from_db()
        self.assertFalse(credential.is_active)
        self.assertIsNotNone(credential.metadata.get('deleted_at'))
    
    def test_update_last_used(self):
        """Test updating last used timestamp."""
        credential = CredentialFactory()
        
        # Update last used
        credential.update_last_used()
        
        credential.refresh_from_db()
        self.assertIsNotNone(credential.metadata.get('last_used'))
        self.assertTrue(
            'last_used' in credential.metadata
        )


class CredentialManagerTest(TestCase):
    """Test cases for CredentialManager."""
    
    def test_get_encryption_key(self):
        """Test getting encryption key."""
        from apps.credentials.models import CredentialManager
        
        # Should use settings encryption key if available
        with patch('apps.credentials.models.settings.ENCRYPTION_KEY', 'test_key'):
            manager = CredentialManager()
            key = manager._get_encryption_key()
            self.assertEqual(key, 'test_key')
        
        # Should generate key if not available
        with patch('apps.credentials.models.settings.ENCRYPTION_KEY', None):
            manager = CredentialManager()
            key = manager._get_encryption_key()
            self.assertIsNotNone(key)
            self.assertIsInstance(key, bytes)
    
    def test_search_by_name(self):
        """Test searching credentials by name."""
        matching_credential = CredentialFactory(name="Production SSH Key")
        non_matching_credential = CredentialFactory(name="Test Docker Token")
        
        results = Credential.objects.search("SSH")
        self.assertIn(matching_credential, results)
        self.assertNotIn(non_matching_credential, results)
    
    def test_get_expiring_credentials(self):
        """Test getting credentials that need rotation."""
        # Creating an old credential that needs rotation
        expiring_credential = CredentialFactory()
        expiring_credential.created_at = timezone.now() - timezone.timedelta(days=350)
        expiring_credential.save()
        
        fresh_credential = CredentialFactory()
        
        expiring_credentials = Credential.objects.get_expiring_credentials(days=360)
        self.assertIn(expiring_credential, expiring_credentials)
        self.assertNotIn(fresh_credential, expiring_credentials)
    
    def test_bulk_deactivate(self):
        """Test bulk deactivating credentials."""
        active_credentials = CredentialFactory.create_batch(3, is_active=True)
        inactive_credential = CredentialFactory(is_active=False)
        
        # Deactivate all active credentials
        count = Credential.objects.bulk_deactivate(active_credentials)
        
        self.assertEqual(count, 3)
        
        for credential in active_credentials:
            credential.refresh_from_db()
            self.assertFalse(credential.is_active)
        
        # Inactive credential should remain unchanged
        inactive_credential.refresh_from_db()
        self.assertFalse(inactive_credential.is_active)