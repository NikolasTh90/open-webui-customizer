"""
Test suite for Enhanced Pipeline Service.

This module contains comprehensive tests for the enhanced pipeline functionality
including custom Git repository management, build step execution, and output handling.

Author: Open WebUI Customizer Team
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.services.enhanced_pipeline_service import EnhancedPipelineService
from app.services.git_service import GitService
from app.services.git_repository_service import GitRepositoryService
from app.services.credential_service import CredentialService
from app.models.models import (
    PipelineRun, GitRepository, Credential, 
    ContainerRegistry, BuildOutput
)
from app.exceptions import (
    ValidationError, NotFoundError, PipelineError,
    DatabaseError
)
from app.utils.encryption import generate_encryption_key


class TestEnhancedPipelineService:
    """Test cases for EnhancedPipelineService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock()
    
    @pytest.fixture
    def enhanced_service(self, mock_db):
        """Create enhanced pipeline service with mocked dependencies."""
        service = EnhancedPipelineService(mock_db)
        
        # Mock dependencies
        service.git_service = Mock(spec=GitService)
        service.git_repo_service = Mock(spec=GitRepositoryService)
        service.credential_service = Mock(spec=CredentialService)
        
        return service
    
    @pytest.fixture
    def sample_credential(self):
        """Create a sample credential for testing."""
        return Credential(
            id=1,
            name="Test SSH Key",
            credential_type="ssh",
            encrypted_data="encrypted_data",
            metadata={},
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_repository(self, sample_credential):
        """Create a sample Git repository for testing."""
        return GitRepository(
            id=1,
            name="Test Repository",
            repository_url="git@github.com:user/repo.git",
            repository_type="ssh",
            default_branch="main",
            credential_id=1,
            is_verified=True,
            verification_status="success",
            verification_message="Repository verified",
            is_experimental=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_registry(self):
        """Create a sample container registry for testing."""
        return ContainerRegistry(
            id=1,
            name="Test Registry",
            registry_type="docker_hub",
            base_image="testuser/custom",
            username="testuser",
            password="testpass",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_available_build_steps(self, enhanced_service):
        """Test that available build steps are properly defined."""
        steps = enhanced_service.AVAILABLE_BUILD_STEPS
        
        # Check that all required steps are present
        expected_steps = [
            'clone_repo', 'apply_branding', 'apply_config',
            'create_zip', 'build_image', 'push_registry'
        ]
        
        for step in expected_steps:
            assert step in steps
            assert 'name' in steps[step]
            assert 'description' in steps[step]
            assert 'order' in steps[step]
            assert 'required' in steps[step]
    
    def test_get_default_steps(self, enhanced_service):
        """Test getting default build steps based on output type."""
        # Test ZIP output
        zip_steps = enhanced_service._get_default_steps('zip')
        assert 'clone_repo' in zip_steps
        assert 'create_zip' in zip_steps
        assert 'build_image' not in zip_steps
        
        # Test Docker output
        docker_steps = enhanced_service._get_default_steps('docker_image')
        assert 'clone_repo' in docker_steps
        assert 'build_image' in docker_steps
        assert 'create_zip' not in docker_steps
        
        # Test both outputs
        both_steps = enhanced_service._get_default_steps('both')
        assert 'clone_repo' in both_steps
        assert 'create_zip' in both_steps
        assert 'build_image' in both_steps
    
    def test_validate_step_dependencies(self, enhanced_service):
        """Test step dependency validation."""
        # Valid combination
        valid_steps = ['clone_repo', 'create_zip']
        enhanced_service._validate_step_dependencies(valid_steps)  # Should not raise
        
        # Invalid combination - missing clone_repo
        invalid_steps = ['create_zip']
        with pytest.raises(ValidationError):
            enhanced_service._validate_step_dependencies(invalid_steps)
        
        # Invalid combination - missing build_image for push_registry
        invalid_steps2 = ['clone_repo', 'push_registry']
        with pytest.raises(ValidationError):
            enhanced_service._validate_step_dependencies(invalid_steps2)
    
    def test_get_ordered_steps(self, enhanced_service):
        """Test that build steps are returned in correct order."""
        steps = ['push_registry', 'clone_repo', 'build_image']
        ordered = enhanced_service._get_ordered_steps(steps)
        
        # Check order: clone_repo (1) -> build_image (5) -> push_registry (6)
        assert ordered[0] == 'clone_repo'
        assert ordered[1] == 'build_image'
        assert ordered[2] == 'push_registry'
    
    def test_create_pipeline_run_success(self, enhanced_service, mock_db, sample_repository):
        """Test successful pipeline run creation."""
        # Setup mocks
        enhanced_service.git_repo_service.get_repository.return_value = sample_repository
        
        # Create pipeline run
        pipeline_run = enhanced_service.create_pipeline_run(
            steps_to_execute=['clone_repo', 'create_zip'],
            git_repository_id=1,
            output_type='zip'
        )
        
        # Verify creation
        assert pipeline_run.status == 'pending'
        assert 'clone_repo' in pipeline_run.steps_to_execute
        assert 'create_zip' in pipeline_run.steps_to_execute
        assert pipeline_run.git_repository_id == 1
        assert pipeline_run.output_type == 'zip'
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
    
    def test_create_pipeline_run_invalid_output_type(self, enhanced_service):
        """Test pipeline run creation with invalid output type."""
        with pytest.raises(ValidationError, match="Invalid output type"):
            enhanced_service.create_pipeline_run(output_type='invalid_type')
    
    def test_create_pipeline_run_invalid_steps(self, enhanced_service):
        """Test pipeline run creation with invalid build steps."""
        with pytest.raises(ValidationError, match="Unknown build step"):
            enhanced_service.create_pipeline_run(steps_to_execute=['invalid_step'])
    
    def test_create_pipeline_run_unverified_repo(self, enhanced_service, mock_db):
        """Test pipeline run creation with unverified repository."""
        # Create unverified repository
        unverified_repo = GitRepository(
            id=1,
            name="Unverified Repo",
            repository_url="git@github.com:user/repo.git",
            repository_type="ssh",
            default_branch="main",
            is_verified=False,
            verification_status="failed"
        )
        
        enhanced_service.git_repo_service.get_repository.return_value = unverified_repo
        
        # Should still allow creation but log warning
        pipeline_run = enhanced_service.create_pipeline_run(
            steps_to_execute=['clone_repo'],
            git_repository_id=1
        )
        
        assert pipeline_run.git_repository_id == 1
    
    def test_execute_pipeline_run_success(self, enhanced_service, mock_db, sample_repository):
        """Test successful pipeline execution."""
        # Setup pipeline run
        pipeline_run = PipelineRun(
            id=1,
            status='pending',
            steps_to_execute=['clone_repo', 'create_zip'],
            git_repository_id=1,
            output_type='zip'
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = pipeline_run
        
        # Mock successful step execution
        enhanced_service._execute_build_step = Mock(return_value={'success': True})
        enhanced_service._get_ordered_steps = Mock(return_value=['clone_repo', 'create_zip'])
        enhanced_service._build_outputs = []
        
        # Execute pipeline
        success, message = enhanced_service.execute_pipeline_run(1)
        
        assert success is True
        pipeline_run.status == 'completed'
    
    def test_execute_pipeline_run_not_found(self, enhanced_service, mock_db):
        """Test pipeline execution with non-existent run."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(NotFoundError):
            enhanced_service.execute_pipeline_run(999)
    
    def test_execute_pipeline_run_invalid_status(self, enhanced_service, mock_db):
        """Test pipeline execution with invalid status."""
        pipeline_run = PipelineRun(
            id=1,
            status='running',  # Not pending
            steps_to_execute=['clone_repo']
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = pipeline_run
        
        with pytest.raises(ValidationError, match="not in pending status"):
            enhanced_service.execute_pipeline_run(1)
    
    @patch('app.services.enhanced_pipeline_service.subprocess.run')
    def test_step_clone_repository_custom(self, mock_subprocess, enhanced_service, sample_repository):
        """Test cloning custom repository."""
        # Setup
        pipeline_run = PipelineRun(
            id=1,
            git_repository_id=1
        )
        
        enhanced_service.git_repo_service.get_repository.return_value = sample_repository
        enhanced_service.git_service.clone_repository.return_value = (True, "Success")
        
        # Mock workspace
        with patch.object(enhanced_service, '_get_repository_info', return_value={'commit_hash': 'abc123'}):
            result = enhanced_service._step_clone_repository(pipeline_run, Path('/tmp/test'))
        
        # Verify
        assert result['is_custom'] is True
        assert result['repository_url'] == sample_repository.repository_url
        assert result['commit_hash'] == 'abc123'
    
    @patch('app.services.enhanced_pipeline_service.subprocess.run')
    def test_step_clone_repository_official(self, mock_subprocess, enhanced_service):
        """Test cloning official repository."""
        # Setup
        pipeline_run = PipelineRun(
            id=1,
            git_repository_id=None  # Use official repo
        )
        
        enhanced_service._clone_official_repository = Mock(return_value=(True, "Success"))
        enhanced_service._get_repository_info = Mock(return_value={'commit_hash': 'abc123'})
        
        # Execute
        result = enhanced_service._step_clone_repository(pipeline_run, Path('/tmp/test'))
        
        # Verify
        assert result['is_custom'] is False
        assert result['repository_url'] == enhanced_service.OFFICIAL_REPO['url']
        assert result['commit_hash'] == 'abc123'
    
    @patch('app.services.enhanced_pipeline_service.shutil.make_archive')
    @patch('app.services.enhanced_pipeline_service.Path.stat')
    def test_step_create_zip(self, mock_stat, mock_make_archive, enhanced_service, mock_db):
        """Test creating ZIP archive."""
        # Setup
        pipeline_run = PipelineRun(id=1)
        repo_dir = Path('/tmp/test/repo')
        output_dir = Path('/tmp/test/outputs')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock file size
        mock_stat.return_value.st_size = 1024
        
        # Mock checksum
        enhanced_service._calculate_file_checksum = Mock(return_value='checksum123')
        
        # Execute
        with patch.object(enhanced_service, '_build_outputs', []) as mock_build_outputs:
            result = enhanced_service._step_create_zip(pipeline_run, Path('/tmp/test'))
        
        # Verify
        mock_make_archive.assert_called_once()
        enhanced_service._calculate_file_checksum.assert_called_once()
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    @patch('app.services.enhanced_pipeline_service.subprocess.run')
    def test_step_build_docker_image(self, mock_subprocess, enhanced_service, mock_db):
        """Test building Docker image."""
        # Setup
        pipeline_run = PipelineRun(id=1)
        repo_dir = Path('/tmp/test/repo')
        dockerfile_path = repo_dir / 'Dockerfile'
        
        # Create mock Dockerfile
        with patch('pathlib.Path.exists', return_value=True):
            # Mock successful build
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stderr = ''
            
            # Execute
            with patch.object(enhanced_service, '_build_outputs', []) as mock_build_outputs:
                result = enhanced_service._step_build_docker_image(pipeline_run, Path('/tmp/test'))
        
        # Verify
        assert 'image_tag' in result
        assert 'build_time' in result
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    def test_step_build_docker_image_no_dockerfile(self, enhanced_service):
        """Test building Docker image without Dockerfile."""
        pipeline_run = PipelineRun(id=1)
        repo_dir = Path('/tmp/test/repo')
        
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(PipelineError, match="Dockerfile not found"):
                enhanced_service._step_build_docker_image(pipeline_run, Path('/tmp/test'))
    
    def test_get_build_outputs(self, enhanced_service, mock_db):
        """Test getting build outputs for pipeline run."""
        # Setup
        pipeline_run = PipelineRun(id=1)
        outputs = [
            BuildOutput(id=1, output_type='zip'),
            BuildOutput(id=2, output_type='docker_image')
        ]
        
        enhanced_service._build_outputs = outputs
        
        # Execute
        result = enhanced_service.get_build_outputs(1)
        
        # Verify
        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[0]['output_type'] == 'zip'
        assert result[1]['id'] == 2
        assert result[1]['output_type'] == 'docker_image'
    
    def test_cleanup_expired_outputs(self, enhanced_service, mock_db):
        """Test cleanup of expired build outputs."""
        # Setup expired outputs
        expired_output = BuildOutput(
            id=1,
            output_type='zip',
            file_path='/tmp/test.zip',
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        
        mock_db.query.return_value.filter.return_value.all.return_value = [expired_output]
        
        with patch('app.services.enhanced_pipeline_service.Path.exists', return_value=True):
            with patch('app.services.enhanced_pipeline_service.Path.unlink') as mock_unlink:
                result = enhanced_service.cleanup_expired_outputs()
        
        # Verify
        assert result['total_cleaned'] == 1
        assert result['files_cleaned'] == 1
        mock_unlink.assert_called_once()
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_get_pipeline_statistics(self, enhanced_service, mock_db):
        """Test getting pipeline statistics."""
        # Setup mock data
        mock_runs = [
            PipelineRun(status='completed', started_at=datetime.utcnow()),
            PipelineRun(status='failed', started_at=datetime.utcnow()),
            PipelineRun(status='completed', started_at=datetime.utcnow())
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = mock_runs
        
        # Execute
        stats = enhanced_service.get_pipeline_statistics(30)
        
        # Verify
        assert stats['total_runs'] == 3
        assert stats['completed_runs'] == 2
        assert stats['failed_runs'] == 1
        assert stats['success_rate'] == (2/3 * 100)
    
    def test_get_repository_usage(self, enhanced_service, sample_repository, mock_db):
        """Test getting repository usage statistics."""
        # Setup
        runs = [
            PipelineRun(status='completed', started_at=datetime.utcnow()),
            PipelineRun(status='failed', started_at=datetime.utcnow())
        ]
        
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [sample_repository],  # Repository query
            runs,  # Pipeline runs query
            []  # Build outputs query
        ]
        
        enhanced_service.git_repo_service.get_repository.return_value = sample_repository
        
        # Execute
        usage = enhanced_service.get_repository_usage(1)
        
        # Verify
        assert usage['repository_id'] == 1
        assert usage['repository_name'] == sample_repository.name
        assert usage['total_pipeline_runs'] == 2
        assert usage['completed_runs'] == 1
        assert usage['failed_runs'] == 1
        assert usage['success_rate'] == 50.0


class TestEnhancedPipelineIntegration:
    """Integration tests for enhanced pipeline functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_build_workspace_creation(self, temp_dir):
        """Test build workspace creation and cleanup."""
        service = EnhancedPipelineService(Mock())
        service.build_dir = temp_dir
        
        # Create workspace
        workspace = service._create_build_workspace(123)
        
        # Verify workspace exists
        assert workspace.exists()
        assert workspace.is_dir()
        
        # Check workspace structure
        expected_pattern = f"build_123_"
        assert expected_pattern in workspace.name
    
    def test_repository_info_parsing(self, temp_dir):
        """Test getting repository information from cloned repo."""
        service = EnhancedPipelineService(Mock())
        
        # Mock git commands
        with patch('app.services.enhanced_pipeline_service.subprocess.run') as mock_subprocess:
            mock_subprocess.side_effect = [
                Mock(returncode=0, stdout='abc123\n'),  # rev-parse HEAD
                Mock(returncode=0, stdout='git@github.com:user/repo.git\n'),  # remote URL
                Mock(returncode=0, stdout='main\n')  # current branch
            ]
            
            info = service._get_repository_info(temp_dir)
            
            assert info['commit_hash'] == 'abc123'
            assert info['remote_url'] == 'git@github.com:user/repo.git'
            assert info['current_branch'] == 'main'
    
    def test_file_checksum_calculation(self, temp_dir):
        """Test SHA-256 checksum calculation."""
        service = EnhancedPipelineService(Mock())
        
        # Create test file
        test_file = temp_dir / 'test.txt'
        test_file.write_text('test content')
        
        # Calculate checksum
        checksum = service._calculate_file_checksum(test_file)
        
        # Verify checksum format (64 hex characters)
        assert len(checksum) == 64
        assert all(c in '0123456789abcdef' for c in checksum.lower())
    
    def test_update_pipeline_status(self, mock_db):
        """Test updating pipeline run status."""
        service = EnhancedPipelineService(mock_db)
        
        # Create pipeline run
        pipeline_run = PipelineRun(
            id=1,
            status='running',
            logs='Existing logs\n'
        )
        
        # Update status
        service._update_pipeline_status(pipeline_run, 'completed', 'Pipeline completed')
        
        # Verify updates
        assert pipeline_run.status == 'completed'
        assert pipeline_run.completed_at is not None
        assert 'Pipeline completed' in pipeline_run.logs
        mock_db.commit.assert_called()
    
    def test_log_to_pipeline(self, mock_db):
        """Test adding logs to pipeline run."""
        service = EnhancedPipelineService(mock_db)
        
        # Create pipeline run
        pipeline_run = PipelineRun(
            id=1,
            logs='Initial log\n'
        )
        
        # Add log message
        service._log_to_pipeline(pipeline_run, 'New log message')
        
        # Verify log addition
        assert 'New log message' in pipeline_run.logs
        mock_db.commit.assert_called()