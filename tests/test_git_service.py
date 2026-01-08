"""
Test suite for Git Service.

This module contains comprehensive tests for the Git service functionality
including repository cloning, validation, and verification.

Author: Open WebUI Customizer Team
"""

import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.services.git_service import GitService
from app.models.models import GitRepository, Credential
from app.exceptions import (
    ValidationError, NotFoundError, PipelineError,
    FileOperationError
)


class TestGitService:
    """Test cases for GitService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock()
    
    @pytest.fixture
    def git_service(self, mock_db):
        """Create Git service with mocked dependencies."""
        service = GitService(mock_db)
        service.credential_service = Mock()
        return service
    
    @pytest.fixture
    def ssh_credential(self):
        """Create a sample SSH credential."""
        return Credential(
            id=1,
            name="Test SSH Key",
            credential_type="ssh",
            encrypted_data="encrypted_ssh_data",
            metadata={"key_type": "rsa"},
            is_active=True
        )
    
    @pytest.fixture
    def https_credential(self):
        """Create a sample HTTPS credential."""
        return Credential(
            id=2,
            name="Test Token",
            credential_type="https",
            encrypted_data="encrypted_https_data",
            metadata={"username": "testuser"},
            is_active=True
        )
    
    @pytest.fixture
    def ssh_repository(self, ssh_credential):
        """Create a sample SSH repository."""
        return GitRepository(
            id=1,
            name="SSH Repository",
            repository_url="git@github.com:user/test-repo.git",
            repository_type="ssh",
            default_branch="main",
            credential_id=1,
            is_verified=True,
            verification_status="success"
        )
    
    @pytest.fixture
    def https_repository(self, https_credential):
        """Create a sample HTTPS repository."""
        return GitRepository(
            id=2,
            name="HTTPS Repository",
            repository_url="https://github.com/user/test-repo.git",
            repository_type="https",
            default_branch="main",
            credential_id=2,
            is_verified=True,
            verification_status="success"
        )
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_ssh_url_validation(self, git_service):
        """Test SSH URL validation."""
        # Valid SSH URLs
        valid_ssh_urls = [
            'git@github.com:user/repo.git',
            'git@gitlab.com:user/repo.git',
            'ssh://git@github.com/user/repo.git',
            'git@bitbucket.org:user/repo.git'
        ]
        
        for url in valid_ssh_urls:
            is_valid, repo_type, normalized = git_service.validate_repository_url(url)
            assert is_valid is True
            assert repo_type == 'ssh'
            assert normalized == url
    
    def test_https_url_validation(self, git_service):
        """Test HTTPS URL validation."""
        # Valid HTTPS URLs
        valid_https_urls = [
            'https://github.com/user/repo.git',
            'https://gitlab.com/user/repo.git',
            'https://bitbucket.org/user/repo.git',
            'https://github.com/user/repo'  # Without .git
        ]
        
        for url in valid_https_urls:
            is_valid, repo_type, normalized = git_service.validate_repository_url(url)
            assert is_valid is True
            assert repo_type == 'https'
            # Should normalize by adding .git if missing
            assert normalized.endswith('.git')
    
    def test_invalid_url_validation(self, git_service):
        """Test invalid URL validation."""
        invalid_urls = [
            '',  # Empty
            'not-a-url',
            'ftp://example.com/repo.git',
            'http://github.com/user/repo.git',  # HTTP not supported
            'https:/github.com/user/repo.git',  # Malformed
            'github.com/user/repo.git'  # Missing protocol
        ]
        
        for url in invalid_urls:
            is_valid, repo_type, error_msg = git_service.validate_repository_url(url)
            assert is_valid is False
            assert repo_type is None
            assert 'Invalid repository URL format' in error_msg or 'Empty repository URL' in error_msg
    
    def test_clone_repository_ssh_success(self, git_service, ssh_repository, temp_dir):
        """Test successful SSH repository cloning."""
        # Mock successful git clone
        with patch('app.services.git_service.subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stderr = ''
            
            with patch.object(git_service, '_get_repository_info', return_value={'commit_hash': 'abc123'}):
                success, message = git_service.clone_repository(
                    ssh_repository, str(temp_dir / 'clone'), 'main'
                )
        
        assert success is True
        assert 'Successfully cloned' in message
        assert 'abc123' in message
        
        # Verify git clone was called with correct parameters
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert 'git' in call_args
        assert 'clone' in call_args
        assert '--branch' in call_args
        assert 'main' in call_args
    
    def test_clone_repository_https_success(self, git_service, https_repository, temp_dir):
        """Test successful HTTPS repository cloning."""
        # Mock credential decryption
        git_service.credential_service.get_decrypted_credential.return_value = {
            'username': 'testuser',
            'password_or_token': 'testtoken'
        }
        
        with patch('app.services.git_service.subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stderr = ''
            
            with patch.object(git_service, '_get_repository_info', return_value={'commit_hash': 'def456'}):
                success, message = git_service.clone_repository(
                    https_repository, str(temp_dir / 'clone'), 'main'
                )
        
        assert success is True
        assert 'Successfully cloned' in message
        
        # Verify environment was set up for HTTPS
        env = mock_subprocess.call_args[1]['env']
        assert 'GIT_ASKPASS' in env
        assert 'GIT_USERNAME' in env
    
    def test_clone_repository_failure(self, git_service, ssh_repository, temp_dir):
        """Test repository cloning failure."""
        # Mock failed git clone
        with patch('app.services.git_service.subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 1
            mock_subprocess.return_value.stderr = 'Authentication failed'
            
            success, message = git_service.clone_repository(
                ssh_repository, str(temp_dir / 'clone'), 'main'
            )
        
        assert success is False
        assert 'Clone failed' in message
        assert 'Authentication failed' in message
    
    def test_clone_repository_timeout(self, git_service, ssh_repository, temp_dir):
        """Test repository cloning timeout."""
        # Mock timeout
        with patch('app.services.git_service.subprocess.run', side_effect=subprocess.TimeoutExpired('git', 300)):
            success, message = git_service.clone_repository(
                ssh_repository, str(temp_dir / 'clone'), 'main'
            )
        
        assert success is False
        assert 'timed out' in message
    
    def test_verify_repository_success(self, git_service, ssh_repository, mock_db):
        """Test successful repository verification."""
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = ssh_repository
        mock_db.commit = Mock()
        
        # Mock successful ls-remote
        with patch('app.services.git_service.subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stdout = 'abc123 refs/heads/main\ndef456 refs/heads/develop'
            
            is_verified, message = git_service.verify_repository(1)
        
        assert is_verified is True
        assert 'Verified - 2 branches accessible' in message
        assert ssh_repository.is_verified is True
        mock_db.commit.assert_called()
    
    def test_verify_repository_failure(self, git_service, ssh_repository, mock_db):
        """Test repository verification failure."""
        mock_db.query.return_value.filter.return_value.first.return_value = ssh_repository
        mock_db.commit = Mock()
        
        # Mock failed ls-remote
        with patch('app.services.git_service.subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 1
            mock_subprocess.return_value.stderr = 'Permission denied'
            
            is_verified, message = git_service.verify_repository(1)
        
        assert is_verified is False
        assert 'Access denied' in message
        assert ssh_repository.is_verified is False
        mock_db.commit.assert_called()
    
    def test_verify_repository_not_found(self, git_service, mock_db):
        """Test verification of non-existent repository."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(NotFoundError):
            git_service.verify_repository(999)
    
    @patch('app.services.git_service.os.chmod')
    @patch('app.services.git_service.tempfile.mkstemp')
    def test_write_temp_ssh_key(self, mock_mkstemp, mock_chmod, git_service):
        """Test writing temporary SSH key."""
        # Mock temp file creation
        mock_fd = 1
        mock_path = '/tmp/test_key'
        mock_mkstemp.return_value = (mock_fd, mock_path)
        
        mock_file = Mock()
        with patch('builtins.open', return_value=mock_file) as mock_open:
            mock_open.return_value.__enter__ = Mock(return_value=mock_file)
            mock_open.return_value.__exit__ = Mock(return_value=None)
            
            result = git_service._write_temp_ssh_key('private_key_content')
        
        assert result == mock_path
        mock_chmod.assert_called_once_with(mock_path, 0o600)
        mock_file.write.assert_called_once_with('private_key_content\n')
        assert 'ssh_key' in git_service._temp_files
    
    @patch('app.services.git_service.tempfile.mkstemp')
    def test_write_temp_known_hosts(self, mock_mkstemp, git_service):
        """Test writing temporary known hosts file."""
        mock_fd = 1
        mock_path = '/tmp/known_hosts'
        mock_mkstemp.return_value = (mock_fd, mock_path)
        
        mock_file = Mock()
        with patch('builtins.open', return_value=mock_file) as mock_open:
            mock_open.return_value.__enter__ = Mock(return_value=mock_file)
            mock_open.return_value.__exit__ = Mock(return_value=None)
            
            result = git_service._write_temp_known_hosts('known_hosts_content')
        
        assert result == mock_path
        mock_file.write.assert_called_once_with('known_hosts_content\n')
        assert 'known_hosts' in git_service._temp_files
    
    @patch('app.services.git_service.os.chmod')
    @patch('app.services.git_service.tempfile.mkstemp')
    def test_create_askpass_script(self, mock_mkstemp, mock_chmod, git_service):
        """Test creating GIT_ASKPASS script."""
        mock_fd = 1
        mock_path = '/tmp/askpass.sh'
        mock_mkstemp.return_value = (mock_fd, mock_path)
        
        mock_file = Mock()
        with patch('builtins.open', return_value=mock_file) as mock_open:
            mock_open.return_value.__enter__ = Mock(return_value=mock_file)
            mock_open.return_value.__exit__ = Mock(return_value=None)
            
            result = git_service._create_askpass_script('testuser', 'testtoken')
        
        assert result == mock_path
        mock_chmod.assert_called_once_with(mock_path, 0o700)
        script_content = mock_file.write.call_args[0][0]
        assert '#!/bin/bash' in script_content
        assert 'testtoken' in script_content
        assert 'askpass_script' in git_service._temp_files
    
    def test_setup_credential_environment_ssh(self, git_service, ssh_credential):
        """Test setting up SSH credential environment."""
        cred_data = {'private_key': 'ssh_key_content'}
        
        with patch.object(git_service, '_write_temp_ssh_key', return_value='/tmp/ssh_key'):
            env = git_service._setup_credential_environment('ssh', cred_data, {})
        
        assert 'GIT_SSH_COMMAND' in env
        ssh_cmd = env['GIT_SSH_COMMAND']
        assert 'ssh -i /tmp/ssh_key' in ssh_cmd
        assert 'StrictHostKeyChecking=no' in ssh_cmd
    
    def test_setup_credential_environment_ssh_with_known_hosts(self, git_service, ssh_credential):
        """Test setting up SSH credential environment with known hosts."""
        cred_data = {
            'private_key': 'ssh_key_content',
            'known_hosts': 'github.com ssh-rsa AAAAB3NzaC1yc2E...'
        }
        
        with patch.object(git_service, '_write_temp_ssh_key', return_value='/tmp/ssh_key'), \
             patch.object(git_service, '_write_temp_known_hosts', return_value='/tmp/known_hosts'):
            env = git_service._setup_credential_environment('ssh', cred_data, {})
        
        ssh_cmd = env['GIT_SSH_COMMAND']
        assert 'UserKnownHostsFile=/tmp/known_hosts' in ssh_cmd
    
    def test_setup_credential_environment_https(self, git_service, https_credential):
        """Test setting up HTTPS credential environment."""
        cred_data = {'username': 'testuser', 'password_or_token': 'testtoken'}
        
        with patch.object(git_service, '_create_askpass_script', return_value='/tmp/askpass.sh'):
            env = git_service._setup_credential_environment('https', cred_data, {})
        
        assert env['GIT_ASKPASS'] == '/tmp/askpass.sh'
        assert env['GIT_USERNAME'] == 'testuser'
    
    def test_cleanup_temp_credentials(self, git_service):
        """Test cleanup of temporary credential files."""
        # Add some temp files
        git_service._temp_files = {
            'ssh_key': Path('/tmp/ssh_key'),
            'known_hosts': Path('/tmp/known_hosts'),
            'askpass_script': Path('/tmp/askpass.sh')
        }
        
        # Mock file operations
        with patch('app.services.git_service.Path.exists', return_value=True), \
             patch('app.services.git_service.Path.unlink') as mock_unlink:
            
            git_service._cleanup_temp_credentials()
        
        # Verify cleanup
        assert len(git_service._temp_files) == 0
        assert mock_unlink.call_count == 3
    
    def test_get_repository_info(self, git_service, ssh_repository, mock_db):
        """Test getting repository information."""
        mock_db.query.return_value.filter.return_value.first.return_value = ssh_repository
        
        with patch('app.services.git_service.subprocess.run') as mock_subprocess:
            mock_subprocess.side_effect = [
                Mock(returncode=0, stdout='abc123\n'),  # rev-parse HEAD
                Mock(returncode=0, stdout='git@github.com:user/repo.git\n'),  # remote URL
                Mock(returncode=0, stdout='main\n')  # current branch
            ]
            
            info = git_service.get_repository_info(1)
        
        assert info['id'] == 1
        assert info['name'] == 'SSH Repository'
        assert info['repository_type'] == 'ssh'
        assert info['host'] == 'github.com'
        assert info['owner'] == 'user'
        assert info['repo_name'] == 'repo'
    
    def test_get_repository_info_not_found(self, git_service, mock_db):
        """Test getting info for non-existent repository."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(NotFoundError):
            git_service.get_repository_info(999)


class TestGitServiceIntegration:
    """Integration tests for Git service functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_create_and_cleanup_build_directory(self, temp_dir):
        """Test creation and cleanup of build directories."""
        git_service = GitService(Mock())
        
        # Create workspace
        workspace = git_service._create_build_workspace(123, temp_dir)
        
        # Verify workspace exists
        assert workspace.exists()
        assert workspace.is_dir()
        assert 'build_123_' in workspace.name
        
        # Cleanup should work
        shutil.rmtree(workspace)
        assert not workspace.exists()
    
    def test_ssh_key_file_permissions(self, temp_dir):
        """Test that SSH key files have correct permissions."""
        git_service = GitService(Mock())
        
        # Actually create a temporary SSH key file
        ssh_key_path = git_service._write_temp_ssh_key('test_private_key')
        
        try:
            # Verify file exists and has correct permissions
            assert Path(ssh_key_path).exists()
            
            # On Unix systems, check file permissions
            if hasattr(os, 'stat'):
                file_stat = os.stat(ssh_key_path)
                # File should be readable/writable by owner only (0o600)
                assert file_stat.st_mode & 0o777 == 0o600
            
            # Verify content
            with open(ssh_key_path, 'r') as f:
                content = f.read()
                assert 'test_private_key' in content
                assert content.endswith('\n')
            
        finally:
            git_service._cleanup_temp_credentials()
            assert not Path(ssh_key_path).exists()
    
    def test_known_hosts_file_creation(self, temp_dir):
        """Test creation of known hosts file."""
        git_service = GitService(Mock())
        
        known_hosts_content = "github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC..."
        known_hosts_path = git_service._write_temp_known_hosts(known_hosts_content)
        
        try:
            assert Path(known_hosts_path).exists()
            
            with open(known_hosts_path, 'r') as f:
                content = f.read()
                assert known_hosts_content.strip() in content
                assert content.endswith('\n')
                
        finally:
            git_service._cleanup_temp_credentials()
            assert not Path(known_hosts_path).exists()
    
    def test_askpass_script_creation(self, temp_dir):
        """Test creation of GIT_ASKPASS script."""
        git_service = GitService(Mock())
        
        script_path = git_service._create_askpass_script('testuser', 'testtoken123')
        
        try:
            assert Path(script_path).exists()
            
            with open(script_path, 'r') as f:
                content = f.read()
                assert '#!/bin/bash' in content
                assert 'echo "testtoken123"' in content
            
            # Verify script is executable
            if hasattr(os, 'access'):
                assert os.access(script_path, os.X_OK)
                
        finally:
            git_service._cleanup_temp_credentials()
            assert not Path(script_path).exists()
    
    def test_multiple_temp_file_cleanup(self, temp_dir):
        """Test cleanup of multiple temporary files."""
        git_service = GitService(Mock())
        
        # Create multiple temporary files
        ssh_key_path = git_service._write_temp_ssh_key('key1')
        known_hosts_path = git_service._write_temp_known_hosts('hosts1')
        script_path = git_service._create_askpass_script('user1', 'token1')
        
        # Verify all files exist
        assert Path(ssh_key_path).exists()
        assert Path(known_hosts_path).exists()
        assert Path(script_path).exists()
        assert len(git_service._temp_files) == 3
        
        # Cleanup all
        git_service._cleanup_temp_credentials()
        
        # Verify all files are deleted and tracking is cleared
        assert not Path(ssh_key_path).exists()
        assert not Path(known_hosts_path).exists()
        assert not Path(script_path).exists()
        assert len(git_service._temp_files) == 0
    
    def test_cleanup_handles_missing_files(self, temp_dir):
        """Test cleanup handles cases where files are missing."""
        git_service = GitService(Mock())
        
        # Add a temporary file path that doesn't exist
        non_existent_file = Path('/tmp/does_not_exist_ssh_key')
        git_service._temp_files['ssh_key'] = non_existent_file
        
        # Cleanup should not raise an exception
        git_service._cleanup_temp_credentials()
        
        # Tracking should be cleared even if file didn't exist
        assert len(git_service._temp_files) == 0


# Import subprocess for timeout test
import subprocess
import os