
"""
Tests for repositories app models.
"""

import pytest
from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from unittest.mock import patch, MagicMock, mock_open
from apps.repositories.models import GitRepository, RepositoryType, VerificationStatus
from apps.core.tests.factories import (
    GitRepositoryFactory,
    CredentialFactory
)
import tempfile
import shutil
import os


class GitRepositoryTest(TestCase):
    """Test cases for GitRepository model."""
    
    def setUp(self):
        """Set up test data."""
        self.repo = GitRepositoryFactory()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test data."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_git_repository_creation(self):
        """Test GitRepository creation."""
        self.assertTrue(isinstance(self.repo, GitRepository))
        self.assertEqual(str(self.repo), f"{self.repo.name} ({self.repo.get_repository_type_display()})")
    
    def test_git_repository_fields(self):
        """Test GitRepository fields."""
        repo = GitRepository.objects.create(
            name="Test Repository",
            repository_url="https://github.com/test/repo.git",
            repository_type=RepositoryType.GITHUB,
            default_branch="main",
            is_active=True,
            is_verified=True,
            verification_status=VerificationStatus.VERIFIED,
            is_experimental=False,
            credential=CredentialFactory(),
            branch="main",
            commit_hash="abc123def456",
            last_commit_date=timezone.now(),
            clone_path="/tmp/test_repo",
            metadata={"language": "python"}
        )
        
        self.assertEqual(repo.name, "Test Repository")
        self.assertEqual(repo.repository_type, RepositoryType.GITHUB)
        self.assertTrue(repo.is_verified)
        self.assertEqual(repo.metadata["language"], "python")
    
    def test_repository_types(self):
        """Test all repository types."""
        types = [
            RepositoryType.GITHUB,
            RepositoryType.GITLAB,
            RepositoryType.BITBUCKET,
            RepositoryType.GENERIC
        ]
        
        for repo_type in types:
            repo = GitRepositoryFactory(repository_type=repo_type)
            self.assertEqual(repo.repository_type, repo_type)
    
    def test_get_clone_directory(self):
        """Test getting clone directory path."""
        repo = GitRepositoryFactory(name="test-repo")
        
        clone_dir = repo.get_clone_directory()
        expected = f"repositories/{repo.id}-{repo.name.lower().replace(' ', '-')}"
        self.assertEqual(clone_dir, expected)
    
    @override_settings(GIT_BASE_CLONE_DIR=self.temp_dir)
    def test_get_clone_path(self):
        """Test getting full clone path."""
        repo = GitRepositoryFactory(name="test-repo")
        
        clone_path = repo.get_clone_path()
        expected = os.path.join(self.temp_dir, repo.get_clone_directory())
        self.assertEqual(clone_path, expected)
    
    def test_get_git_url_github(self):
        """Test getting Git-formatted URL for GitHub."""
        repo = GitRepositoryFactory(
            repository_type=RepositoryType.GITHUB,
            repository_url="https://github.com/user/repo.git"
        )
        
        git_url = repo.get_git_url()
        self.assertEqual(git_url, "git@github.com:user/repo.git")
    
    def test_get_git_url_gitlab(self):
        """Test getting Git-formatted URL for GitLab."""
        repo = GitRepositoryFactory(
            repository_type=RepositoryType.GITLAB,
            repository_url="https://gitlab.com/user/repo.git"
        )
        
        git_url = repo.get_git_url()
        self.assertEqual(git_url, "git@gitlab.com:user/repo.git")
    
    def test_get_git_url_with_ssh(self):
        """Test getting Git URL when already SSH."""
        repo = GitRepositoryFactory(
            repository_type=RepositoryType.GITHUB,
            repository_url="git@github.com:user/repo.git"
        )
        
        git_url = repo.get_git_url()
        self.assertEqual(git_url, "git@github.com:user/repo.git")
    
    def test_get_web_url_github(self):
        """Test getting web URL for GitHub."""
        repo = GitRepositoryFactory(
            repository_type=RepositoryType.GITHUB,
            repository_url="https://github.com/user/repo.git"
        )
        
        web_url = repo.get_web_url()
        self.assertEqual(web_url, "https://github.com/user/repo")
    
    def test_get_web_url_gitlab(self):
        """Test getting web URL for GitLab."""
        repo = GitRepositoryFactory(
            repository_type=RepositoryType.GITLAB,
            repository_url="https://gitlab.com/user/repo.git"
        )
        
        web_url = repo.get_web_url()
        self.assertEqual(web_url, "https://gitlab.com/user/repo")
    
    def test_get_repository_identifier_github(self):
        """Test getting repository identifier for GitHub."""
        repo = GitRepositoryFactory(
            repository_type=RepositoryType.GITHUB,
            repository_url="https://github.com/user/repo.git"
        )
        
        identifier = repo.get_repository_identifier()
        self.assertEqual(identifier, "user/repo")
    
    def test_get_repository_identifier_generic(self):
        """Test getting repository identifier for generic URLs."""
        repo = GitRepositoryFactory(
            repository_type=RepositoryType.GENERIC,
            repository_url="https://git.example.com/group/project/repo.git"
        )
        
        identifier = repo.get_repository_identifier()
        self.assertEqual(identifier, "group/project/repo")
    
    @patch('apps.repositories.models.Repo')
    def test_verify_repository_success(self, mock_repo_class):
        """Test successful repository verification."""
        # Mock repo validation
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        repo = GitRepositoryFactory()
        result = repo.verify_repository()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Repository verified successfully')
        self.assertTrue(repo.is_verified)
        self.assertEqual(repo.verification_status, VerificationStatus.VERIFIED)
    
    @patch('apps.repositories.models.Repo')
    def test_verify_repository_failure(self, mock_repo_class):
        """Test failed repository verification."""
        # Mock repo validation failure
        mock_repo_class.side_effect = Exception("Invalid repository")
        
        repo = GitRepositoryFactory()
        result = repo.verify_repository()
        
        self.assertFalse(result['success'])
        self.assertIn('Invalid repository', result['message'])
        self.assertFalse(repo.is_verified)
        self.assertEqual(repo.verification_status, VerificationStatus.FAILED)
    
    @patch('apps.repositories.models.Repo')
    def test_test_clone_success(self, mock_repo_class):
        """Test successful clone test."""
        mock_repo = MagicMock()
        mock_repo.clone.return_value = True
        mock_repo_class.return_value = mock_repo
        
        repo = GitRepositoryFactory()
        result = repo.test_clone()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Clone test successful')
    
    @patch('apps.repositories.models.Repo')
    def test_test_clone_failure(self, mock_repo_class):
        """Test failed clone test."""
        mock_repo = MagicMock()
        mock_repo.clone.return_value = False
        mock_repo_class.return_value = mock_repo
        
        repo = GitRepositoryFactory()
        result = repo.test_clone()
        
        self.assertFalse(result['success'])
        self.assertIn('failed', result['message'])
    
    @patch('apps.repositories.models.git')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_clone_repository(self, mock_makedirs, mock_exists, mock_git):
        """Test cloning a repository."""
        mock_exists.return_value = False
        mock_git.Repo.clone_from.return_value = MagicMock()
        
        repo = GitRepositoryFactory()
        
        with patch('builtins.open', mock_open()):
            result = repo.clone_repository()
        
        self.assertTrue(result['success'])
        self.assertIn('cloned successfully', result['message'])
        mock_git.Repo.clone_from.assert_called_once()
    
    @patch('os.path.exists')
    @patch('shutil.rmtree')
    def test_cleanup_clone(self, mock_rmtree, mock_exists):
        """Test cleaning up a cloned repository."""
        mock_exists.return_value = True
        
        repo = GitRepositoryFactory(clone_path="/tmp/test_repo")
        result = repo.cleanup_clone()
        
        self.assertTrue(result)
        mock_rmtree.assert_called_once_with(repo.clone_path)
    
    @patch('apps.repositories.models.Repo')
    def test_update_commit_info(self, mock_repo_class):
        """Test updating commit information."""
        mock_repo = MagicMock()
        mock_repo.head.commit.hexsha = "abc123def456"
        mock_repo.head.commit.committed_datetime = timezone.now()
        mock_repo_class.return_value = mock_repo
        
        repo = GitRepositoryFactory()
        result = repo.update_commit_info()
        
        self.assertTrue(result)
        self.assertEqual(repo.last_commit_hash, "abc123def456")
        self.assertIsNotNone(repo.last_commit_date)
    
    def test_can_be_cloned_property(self):
        """Test can_be_cloned property."""
        # Active, verified repo with credential should be cloneable
        cloneable_repo = GitRepositoryFactory(
            is_active=True,
            is_verified=True,
            credential=CredentialFactory()
        )
        self.assertTrue(cloneable_repo.can_be_cloned)
        
        # Inactive repo should not be cloneable
        inactive_repo = GitRepositoryFactory(is_active=False)
        self.assertFalse(inactive_repo.can_be_cloned)
        
        # Unverified repo should not be cloneable
        unverified_repo = GitRepositoryFactory(is_verified=False)
        self.assertFalse(unverified_repo.can_be_cloned)
    
    def test_is_recently_updated_property(self):
        """Test is_recently_updated property."""
        # Recently updated repo
        recent_repo = GitRepositoryFactory(
            last_commit_date=timezone.now() - timezone.timedelta(days=5)
        )
        self.assertTrue(recent_repo.is_recently_updated)
        
        # Old repo
        old_repo = GitRepositoryFactory(
            last_commit_date=timezone.now() - timezone.timedelta(days=40)
        )
        self.assertFalse(old_repo.is_recently_updated)
    
    def test_get_branches(self):
        """Test getting repository branches."""
        with patch('apps.repositories.models.Repo') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.branches = ['main', 'develop', 'feature/test']
            mock_repo_class.return_value = mock_repo
            
            repo = GitRepositoryFactory()
            branches = repo.get_branches()
            
            self.assertEqual(len(branches), 3)
            self.assertIn('main', branches)
            self.assertIn('develop', branches)
    
    def test_get_tags(self):
        """Test getting repository tags."""
        with patch('apps.repositories.models.Repo') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.tags = ['v1.0.0', 'v1.1.0', 'v2.0.0']
            mock_repo_class.return_value = mock_repo
            
            repo = GitRepositoryFactory()
            tags = repo.get_tags()
            
            self.assertEqual(len(tags), 3)
            self.assertIn('v1.0.0', tags)
            self.assertIn('v2.0.0', tags)


class GitRepositoryManagerTest(TestCase):
    """Test cases for GitRepositoryManager."""
    
    def test_queryset_active(self):
        """Test custom queryset for active repositories."""
        active_repo = GitRepositoryFactory(is_active=True)
        inactive_repo = GitRepositoryFactory(is_active=False)
        
        active_repos = GitRepository.objects.active()
        self.assertIn(active_repo, active_repos)
        self.assertNotIn(inactive_repo, active_repos)
    
    def test_queryset_verified(self):
        """Test custom queryset for verified repositories."""
        verified_repo = GitRepositoryFactory(is_verified=True)
        unverified_repo = GitRepositoryFactory(is_verified=False)
        
        verified_repos = GitRepository.objects.verified()
        self.assertIn(verified_repo, verified_repos)
        self.assertNotIn(unverified_repo, verified_repos)
    
    def test_queryset_by_repository_type(self):
        """Test filtering by repository type."""
        github_repo = GitRepositoryFactory(repository_type=RepositoryType.GITHUB)
        gitlab_repo = GitRepositoryFactory(repository_type=RepositoryType.GITLAB)
        
        github_repos = GitRepository.objects.by_repository_type(RepositoryType.GITHUB)
        self.assertIn(github_repo, github_repos)
        self.assertNotIn(gitlab_repo, github_repos)
    
    def test_queryset_experimental(self):
        """Test getting experimental repositories."""
        experimental_repo = GitRepositoryFactory(is_experimental=True)
        production_repo = GitRepositoryFactory(is_experimental=False)
        
        experimental_repos = GitRepository.objects.experimental()
        self.assertIn(experimental_repo, experimental_repos)
        self.assertNotIn(production_repo, experimental_repos)
    
    def test_search_by_name(self):
        """Test searching repositories by name."""
        matching_repo = GitRepositoryFactory(name="Test Repository")
        non_matching_repo = GitRepositoryFactory(name="Production Repo")
        
        results = GitRepository.objects.search("Test")
        self.assertIn(matching_repo, results)
        self.assertNotIn(non_matching_repo, results)
    
    def test_get_stale_repositories(self):
        """Test getting stale repositories."""
        # Stale repo (not updated recently)
        stale_repo = GitRepositoryFactory(
            last_commit_date=timezone.now() - timezone.timedelta(days=40)
        )
        
        # Recent repo
        recent_repo = GitRepositoryFactory(
            last_commit_date=timezone.now() - timezone.timedelta(days=5)
        )
        
        stale_repos = GitRepository.objects.get_stale_repositories(days=30)
        self.assertIn(stale_repo, stale_repos)
        self.assertNotIn(recent_repo, stale_repos)
    
    def test_bulk_verify_repositories(self):
        """Test bulk verification of repositories."""
        repos = GitRepositoryFactory.create_batch(3, verification_status=VerificationStatus.PENDING)
        
        with patch('apps.repositories.models.GitRepository.verify_repository') as mock_verify:
            mock_verify.return_value = {'success': True}
            
            count = GitRepository.objects.bulk_verify(repos)
            
            self.assertEqual(count, 3)
            for repo in repos:
                repo.refresh_from_db()
                self.assertEqual(repo.verification_status, VerificationStatus.VERIFIED)
    
    def test_get_repository_statistics(self):
        """Test getting repository statistics."""
        # Create repos with different statuses
        active_verified = GitRepositoryFactory(is_active=True, is_verified=True)
        active_unverified = GitRepositoryFactory(is_active=True, is_verified=False)
        inactive_verified = GitRepositoryFactory(is_active=False, is_verified=True)
        experimental = GitRepositoryFactory(is_experimental=True)
        
        stats = GitRepository.objects.get_repository_statistics()
        
        self.assertEqual(stats['total'], 4)
        self.assertEqual(stats['active'], 2)
        self.assertEqual(stats['verified'], 2)
        self.assertEqual(stats['experimental'], 1)
        self.assertEqual(stats['success_rate'], 50.0)  # 2 out of 4 are both active and verified
    
    def test_sync_repositories(self):
        """Test syncing repositories with remote."""
        repos = GitRepositoryFactory.create_batch(2)
        
        with patch('apps.repositories.models.GitRepository.update_commit_info') as mock_update:
            mock_update.return_value = True
            
            count = GitRepository.objects.sync_repositories(repos)
            
            self.assertEqual(count, 2)
            self.assertEqual(mock_update.call_count, 2)