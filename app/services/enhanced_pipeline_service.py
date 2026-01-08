"""
Enhanced Pipeline Service for Custom Fork Cloning.

This service extends the existing pipeline functionality to support
cloning custom Git forks, building from custom repositories, and
generating both ZIP files and Docker images.

Author: Open WebUI Customizer Team
"""

import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

from app.models.models import (
    PipelineRun, GitRepository, ContainerRegistry, 
    Credential, BuildOutput
)
from app.services.git_repository_service import GitRepositoryService
from app.services.git_service import GitService
from app.services.credential_service import CredentialService
from app.exceptions import (
    PipelineError, ValidationError, NotFoundError,
    DatabaseError, FileOperationError
)
from app.utils.logging import get_logger, log_function_call

logger = get_logger(__name__)


class EnhancedPipelineService:
    """
    Enhanced pipeline service with custom fork cloning support.
    
    Extends the base pipeline service to support:
    - Custom Git repository cloning
    - Flexible build steps selection
    - ZIP file generation
    - Docker image building
    - Registry pushing
    - Build output tracking
    """
    
    # Official repository info (for reference/fallback)
    OFFICIAL_REPO = {
        'url': 'https://github.com/open-webui/open-webui.git',
        'default_branch': 'main'
    }
    
    # Available build steps and default order
    AVAILABLE_BUILD_STEPS = {
        'clone_repo': {
            'name': 'Clone Git Repository',
            'description': 'Clone the Git repository (official or custom fork)',
            'order': 1,
            'required': True
        },
        'apply_branding': {
            'name': 'Apply Branding Template',
            'description': 'Apply selected branding template',
            'order': 2,
            'required': False
        },
        'apply_config': {
            'name': 'Apply Configuration',
            'description': 'Apply custom configuration settings',
            'order': 3,
            'required': False
        },
        'create_zip': {
            'name': 'Create ZIP Archive',
            'description': 'Package customizations into a ZIP file',
            'order': 4,
            'required': False
        },
        'build_image': {
            'name': 'Build Docker Image',
            'description': 'Build custom Docker image',
            'order': 5,
            'required': False
        },
        'push_registry': {
            'name': 'Push to Registry',
            'description': 'Push Docker image to container registry',
            'order': 6,
            'required': False
        }
    }
    
    def __init__(self, db: Session):
        """
        Initialize the enhanced pipeline service.
        
        Args:
            db: Database session for persistence operations
        """
        self.db = db
        self.git_service = GitService(db)
        self.git_repo_service = GitRepositoryService(db)
        self.credential_service = CredentialService(db)
        
        # Working directory for builds (temporary)
        self.build_dir = Path(tempfile.gettempdir()) / 'open_webui_builds'
        self.build_dir.mkdir(exist_ok=True)
        
        logger.info("Enhanced pipeline service initialized")
    
    @log_function_call
    def create_pipeline_run(
        self,
        steps_to_execute: Optional[List[str]] = None,
        git_repository_id: Optional[int] = None,
        branding_template_id: Optional[int] = None,
        configuration_id: Optional[int] = None,
        output_type: str = "zip",
        registry_id: Optional[int] = None,
        custom_parameters: Optional[Dict[str, Any]] = None
    ) -> PipelineRun:
        """
        Create a new pipeline run with custom fork support.
        
        Args:
            steps_to_execute: List of build steps to execute
            git_repository_id: Optional custom Git repository ID
            branding_template_id: Optional branding template ID
            configuration_id: Optional configuration ID
            output_type: Output type ('zip' or 'docker_image')
            registry_id: Optional container registry ID
            custom_parameters: Additional custom parameters
            
        Returns:
            Created PipelineRun instance
            
        Raises:
            ValidationError: If parameters are invalid
            NotFoundError: If referenced resources don't exist
            DatabaseError: If database operation fails
        """
        try:
            # Validate output type
            valid_output_types = ['zip', 'docker_image', 'both']
            if output_type not in valid_output_types:
                raise ValidationError(
                    f"Invalid output type. Must be one of: {', '.join(valid_output_types)}"
                )
            
            # Validate steps to execute
            if not steps_to_execute:
                steps_to_execute = self._get_default_steps(output_type)
            
            # Validate each step
            for step in steps_to_execute:
                if step not in self.AVAILABLE_BUILD_STEPS:
                    raise ValidationError(f"Unknown build step: {step}")
            
            # Check step dependencies
            self._validate_step_dependencies(steps_to_execute)
            
            # Validate Git repository if provided
            git_repo = None
            if git_repository_id:
                git_repo = self.git_repo_service.get_repository(git_repository_id)
                
                # Verify repository is accessible
                if not git_repo.is_verified:
                    logger.warning(f"Using unverified repository", extra={
                        'repository_id': git_repository_id,
                        'repository_name': git_repo.name
                    })
            
            # Validate registry if required
            if 'push_registry' in steps_to_execute:
                if not registry_id:
                    raise ValidationError("Registry ID is required when pushing to registry")
                
                registry = self.db.query(ContainerRegistry).filter(
                    ContainerRegistry.id == registry_id
                ).first()
                
                if not registry:
                    raise NotFoundError(f"Registry with ID {registry_id} not found")
            
            # Additional validation based on steps
            if 'apply_branding' in steps_to_execute and not branding_template_id:
                raise ValidationError("Branding template ID is required when applying branding")
            
            if 'apply_config' in steps_to_execute and not configuration_id:
                raise ValidationError("Configuration ID is required when applying configuration")
            
            # Create pipeline run
            pipeline_run = PipelineRun(
                status='pending',
                steps_to_execute=steps_to_execute,
                git_repository_id=git_repository_id,
                output_type=output_type,
                registry_id=registry_id,
                logs='Pipeline run created. Waiting for execution.\n'
            )
            
            self.db.add(pipeline_run)
            self.db.commit()
            self.db.refresh(pipeline_run)
            
            logger.info(f"Created enhanced pipeline run", extra={
                'pipeline_run_id': pipeline_run.id,
                'steps': steps_to_execute,
                'output_type': output_type,
                'git_repository_id': git_repository_id
            })
            
            return pipeline_run
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create pipeline run: {str(e)}")
            raise DatabaseError(f"Failed to create pipeline run: {str(e)}")
    
    @log_function_call
    def execute_pipeline_run(self, run_id: int) -> Tuple[bool, str]:
        """
        Execute a pipeline run with custom fork cloning.
        
        Args:
            run_id: Pipeline run ID to execute
            
        Returns:
            Tuple of (success, message)
            
        Raises:
            NotFoundError: If pipeline run doesn't exist
            PipelineError: If execution fails
        """
        try:
            # Get pipeline run
            pipeline_run = self.db.query(PipelineRun).filter(
                PipelineRun.id == run_id
            ).first()
            
            if not pipeline_run:
                raise NotFoundError(f"Pipeline run with ID {run_id} not found")
            
            if pipeline_run.status != 'pending':
                raise ValidationError(f"Pipeline run {run_id} is not in pending status")
            
            logger.info(f"Executing pipeline run", extra={
                'pipeline_run_id': run_id,
                'steps': pipeline_run.steps_to_execute
            })
            
            # Update status to running
            self._update_pipeline_status(pipeline_run, 'running', 'Starting pipeline execution...')
            
            # Create build workspace
            build_workspace = self._create_build_workspace(run_id)
            
            try:
                # Execute build steps in order
                step_results = {}
                for step in self._get_ordered_steps(pipeline_run.steps_to_execute):
                    start_time = time.time()
                    
                    self._update_pipeline_status(
                        pipeline_run, 
                        'running', 
                        f'Executing step: {self.AVAILABLE_BUILD_STEPS[step]["name"]}'
                    )
                    
                    try:
                        result = self._execute_build_step(
                            step, pipeline_run, build_workspace
                        )
                        step_results[step] = {
                            'success': True,
                            'result': result,
                            'duration_seconds': time.time() - start_time
                        }
                        
                        self._log_to_pipeline(
                            pipeline_run,
                            f"✓ Step completed: {self.AVAILABLE_BUILD_STEPS[step]['name']}"
                        )
                        
                    except Exception as e:
                        step_results[step] = {
                            'success': False,
                            'error': str(e),
                            'duration_seconds': time.time() - start_time
                        }
                        
                        self._log_to_pipeline(
                            pipeline_run,
                            f"✗ Step failed: {self.AVAILABLE_BUILD_STEPS[step]['name']} - {str(e)}"
                        )
                        
                        # Stop execution on step failure
                        break
                
                # Check overall success
                failed_steps = [
                    step for step, result in step_results.items() 
                    if not result['success']
                ]
                
                if failed_steps:
                    self._update_pipeline_status(
                        pipeline_run,
                        'failed',
                        f"Pipeline failed. Failed steps: {', '.join(failed_steps)}"
                    )
                    
                    logger.error(f"Pipeline run failed", extra={
                        'pipeline_run_id': run_id,
                        'failed_steps': failed_steps
                    })
                    
                    return False, f"Pipeline failed in steps: {', '.join(failed_steps)}"
                
                # Pipeline completed successfully
                outputs = self._get_build_outputs(pipeline_run)
                
                self._update_pipeline_status(
                    pipeline_run,
                    'completed',
                    f"Pipeline completed successfully. Generated {len(outputs)} output(s)."
                )
                
                logger.info(f"Pipeline run completed successfully", extra={
                    'pipeline_run_id': run_id,
                    'outputs_count': len(outputs)
                })
                
                return True, f"Pipeline completed successfully with {len(outputs)} output(s)"
                
            finally:
                # Clean up build workspace
                if build_workspace.exists():
                    shutil.rmtree(build_workspace, ignore_errors=True)
                    logger.debug(f"Cleaned up build workspace", extra={
                        'workspace_path': str(build_workspace)
                    })
        
        except (NotFoundError, ValidationError, PipelineError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing pipeline run: {str(e)}")
            raise PipelineError(f"Pipeline execution failed: {str(e)}")
    
    def _execute_build_step(
        self,
        step: str,
        pipeline_run: PipelineRun,
        build_workspace: Path
    ) -> Dict[str, Any]:
        """Execute a specific build step."""
        
        if step == 'clone_repo':
            return self._step_clone_repository(pipeline_run, build_workspace)
        
        elif step == 'apply_branding':
            return self._step_apply_branding(pipeline_run, build_workspace)
        
        elif step == 'apply_config':
            return self._step_apply_configuration(pipeline_run, build_workspace)
        
        elif step == 'create_zip':
            return self._step_create_zip(pipeline_run, build_workspace)
        
        elif step == 'build_image':
            return self._step_build_docker_image(pipeline_run, build_workspace)
        
        elif step == 'push_registry':
            return self._step_push_to_registry(pipeline_run, build_workspace)
        
        else:
            raise PipelineError(f"Unknown build step: {step}")
    
    def _step_clone_repository(
        self,
        pipeline_run: PipelineRun,
        build_workspace: Path
    ) -> Dict[str, Any]:
        """Clone the Git repository."""
        
        # Determine repository URL and branch
        if pipeline_run.git_repository_id:
            git_repo = self.git_repo_service.get_repository(pipeline_run.git_repository_id)
            repository_url = git_repo.repository_url
            branch = git_repo.default_branch
            repo_name = git_repo.name
            is_custom = True
        else:
            # Use official repository
            repository_url = self.OFFICIAL_REPO['url']
            branch = self.OFFICIAL_REPO['default_branch']
            repo_name = 'open-webui'
            is_custom = False
        
        # Clone repository
        repo_dir = build_workspace / 'repo'
        
        if is_custom:
            success, message = self.git_service.clone_repository(
                git_repo, str(repo_dir), branch
            )
        else:
            # Clone official repository
            success, message = self._clone_official_repository(
                repository_url, str(repo_dir), branch
            )
        
        if not success:
            raise PipelineError(f"Failed to clone repository: {message}")
        
        # Get repository info
        repo_info = self._get_repository_info(repo_dir)
        
        result = {
            'repository_url': repository_url,
            'branch': branch,
            'commit_hash': repo_info.get('commit_hash'),
            'is_custom': is_custom,
            'repo_name': repo_name
        }
        
        self._log_to_pipeline(
            pipeline_run,
            f"Cloned repository: {repository_url} ({branch}) @ {repo_info.get('commit_hash', 'unknown')[:8]}"
        )
        
        return result
    
    def _clone_official_repository(
        self,
        repository_url: str,
        target_dir: str,
        branch: str = 'main'
    ) -> Tuple[bool, str]:
        """Clone the official Open WebUI repository."""
        
        try:
            target_path = Path(target_dir)
            target_path.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                'git', 'clone', 
                '--depth', '1',
                '--branch', branch,
                repository_url,
                target_dir
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                return False, f"Clone failed: {error_msg}"
            
            return True, "Repository cloned successfully"
            
        except subprocess.TimeoutExpired:
            return False, "Clone operation timed out"
        except Exception as e:
            return False, f"Clone error: {str(e)}"
    
    def _step_apply_branding(
        self,
        pipeline_run: PipelineRun,
        build_workspace: Path
    ) -> Dict[str, Any]:
        """Apply branding template."""
        
        # This would integrate with existing branding functionality
        # For now, we'll mock the implementation
        
        repo_dir = build_workspace / 'repo'
        
        # Get branding template (placeholder)
        # branding_template = get_branding_template(db, pipeline_run.branding_template_id)
        
        # Apply branding placeholder
        result = {
            'template_applied': True,
            'customizations_count': 0  # Would be actual count
        }
        
        self._log_to_pipeline(pipeline_run, "Applied branding template (placeholder)")
        
        return result
    
    def _step_apply_configuration(
        self,
        pipeline_run: PipelineRun,
        build_workspace: Path
    ) -> Dict[str, Any]:
        """Apply configuration settings."""
        
        # This would integrate with existing configuration functionality
        # For now, we'll mock the implementation
        
        repo_dir = build_workspace / 'repo'
        
        # Get configuration (placeholder)
        # configuration = get_configuration(db, pipeline_run.configuration_id)
        
        # Apply configuration placeholder
        result = {
            'config_applied': True,
            'settings_count': 0  # Would be actual count
        }
        
        self._log_to_pipeline(pipeline_run, "Applied configuration settings (placeholder)")
        
        return result
    
    def _step_create_zip(
        self,
        pipeline_run: PipelineRun,
        build_workspace: Path
    ) -> Dict[str, Any]:
        """Create ZIP archive of the custom build."""
        
        repo_dir = build_workspace / 'repo'
        output_dir = build_workspace / 'outputs'
        output_dir.mkdir(exist_ok=True)
        
        # Create ZIP file
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"open_webui_custom_{timestamp}.zip"
        zip_path = output_dir / zip_filename
        
        try:
            # Create ZIP archive
            shutil.make_archive(
                str(zip_path.with_suffix('')),
                'zip',
                str(repo_dir.parent),
                repo_dir.name
            )
            
            # Calculate checksum
            checksum = self._calculate_file_checksum(zip_path)
            file_size = zip_path.stat().st_size
            
            # Store build output
            build_output = BuildOutput(
                pipeline_run_id=pipeline_run.id,
                output_type='zip',
                file_path=str(zip_path),
                file_size_bytes=file_size,
                checksum_sha256=checksum,
                expires_at=datetime.utcnow() + timedelta(days=7)  # 7 days retention
            )
            
            self.db.add(build_output)
            self.db.commit()
            
            result = {
                'zip_filename': zip_filename,
                'file_size_bytes': file_size,
                'checksum': checksum
            }
            
            self._log_to_pipeline(
                pipeline_run,
                f"Created ZIP archive: {zip_filename} ({file_size:,} bytes)"
            )
            
            return result
            
        except Exception as e:
            raise PipelineError(f"Failed to create ZIP archive: {str(e)}")
    
    def _step_build_docker_image(
        self,
        pipeline_run: PipelineRun,
        build_workspace: Path
    ) -> Dict[str, Any]:
        """Build Docker image."""
        
        repo_dir = build_workspace / 'repo'
        
        # Check for Dockerfile
        dockerfile_path = repo_dir / 'Dockerfile'
        if not dockerfile_path.exists():
            raise PipelineError("Dockerfile not found in repository")
        
        # Build Docker image
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        image_tag = f"open-webui-custom:{timestamp}"
        
        try:
            cmd = [
                'docker', 'build',
                '-t', image_tag,
                str(repo_dir)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise PipelineError(f"Docker build failed: {error_msg}")
            
            # Store build output
            build_output = BuildOutput(
                pipeline_run_id=pipeline_run.id,
                output_type='docker_image',
                image_url=image_tag,
                expires_at=datetime.utcnow() + timedelta(days=1)  # 1 day retention
            )
            
            self.db.add(build_output)
            self.db.commit()
            
            result = {
                'image_tag': image_tag,
                'build_time': datetime.utcnow().isoformat()
            }
            
            self._log_to_pipeline(pipeline_run, f"Built Docker image: {image_tag}")
            
            return result
            
        except subprocess.TimeoutExpired:
            raise PipelineError("Docker build timed out")
        except Exception as e:
            raise PipelineError(f"Docker build failed: {str(e)}")
    
    def _step_push_to_registry(
        self,
        pipeline_run: PipelineRun,
        build_workspace: Path
    ) -> Dict[str, Any]:
        """Push Docker image to container registry."""
        
        # Get registry info
        registry = self.db.query(ContainerRegistry).filter(
            ContainerRegistry.id == pipeline_run.registry_id
        ).first()
        
        if not registry:
            raise NotFoundError("Registry configuration not found")
        
        # Get the built image
        build_output = self.db.query(BuildOutput).filter(
            BuildOutput.pipeline_run_id == pipeline_run.id,
            BuildOutput.output_type == 'docker_image'
        ).first()
        
        if not build_output or not build_output.image_url:
            raise PipelineError("No Docker image found to push")
        
        local_image = build_output.image_url
        remote_image = f"{registry.base_image}:custom-{pipeline_run.id}"
        
        try:
            # Tag image for registry
            subprocess.run(
                ['docker', 'tag', local_image, remote_image],
                check=True,
                capture_output=True
            )
            
            # Push to registry
            if registry.registry_type == 'docker_hub' and registry.username:
                # Login and push
                subprocess.run([
                    'docker', 'login',
                    '-u', registry.username,
                    '-p', registry.password,
                    'docker.io'
                ], check=True, capture_output=True)
            
            subprocess.run(
                ['docker', 'push', remote_image],
                check=True,
                capture_output=True,
                timeout=600
            )
            
            # Update build output with remote URL
            build_output.image_url = remote_image
            self.db.commit()
            
            result = {
                'pushed_image_url': remote_image,
                'registry_name': registry.name
            }
            
            self._log_to_pipeline(
                pipeline_run,
                f"Pushed Docker image to registry: {remote_image}"
            )
            
            return result
            
        except subprocess.CalledProcessError as e:
            raise PipelineError(f"Docker push failed: {e.stderr.decode()}")
        except subprocess.TimeoutExpired:
            raise PipelineError("Docker push timed out")
        except Exception as e:
            raise PipelineError(f"Docker push failed: {str(e)}")
    
    def _create_build_workspace(self, run_id: int) -> Path:
        """Create a temporary workspace for the build."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        workspace = self.build_dir / f"build_{run_id}_{timestamp}"
        workspace.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Created build workspace", extra={
            'pipeline_run_id': run_id,
            'workspace_path': str(workspace)
        })
        
        return workspace
    
    def _update_pipeline_status(
        self,
        pipeline_run: PipelineRun,
        status: str,
        message: str
    ) -> None:
        """Update pipeline run status and log message."""
        pipeline_run.status = status
        
        if status in ['completed', 'failed'] and pipeline_run.completed_at is None:
            pipeline_run.completed_at = datetime.utcnow()
        
        pipeline_run.logs += f"[{datetime.utcnow().isoformat()}] {message}\n"
        self.db.commit()
    
    def _log_to_pipeline(self, pipeline_run: PipelineRun, message: str) -> None:
        """Add a log message to the pipeline run."""
        timestamp = datetime.utcnow().isoformat()
        pipeline_run.logs += f"[{timestamp}] {message}\n"
        self.db.commit()
    
    def _get_default_steps(self, output_type: str) -> List[str]:
        """Get default build steps based on output type."""
        base_steps = ['clone_repo']
        
        # Add output-specific steps
        if output_type in ['zip', 'both']:
            base_steps.append('create_zip')
        
        if output_type in ['docker_image', 'both']:
            base_steps.extend(['build_image'])
        
        return base_steps
    
    def _validate_step_dependencies(self, steps: List[str]) -> None:
        """Validate that build step dependencies are satisfied."""
        for step in steps:
            step_info = self.AVAILABLE_BUILD_STEPS[step]
            
            # Check required steps
            if step_info.get('required'):
                if step not in steps:
                    continue  # This is the required step itself
            
            # Check dependencies
            if step == 'create_zip':
                if 'clone_repo' not in steps:
                    raise ValidationError("create_zip requires clone_repo step")
            
            elif step == 'build_image':
                if 'clone_repo' not in steps:
                    raise ValidationError("build_image requires clone_repo step")
            
            elif step == 'push_registry':
                if 'build_image' not in steps:
                    raise ValidationError("push_registry requires build_image step")
            
            elif step == 'apply_branding':
                if 'clone_repo' not in steps:
                    raise ValidationError("apply_branding requires clone_repo step")
            
            elif step == 'apply_config':
                if 'clone_repo' not in steps:
                    raise ValidationError("apply_config requires clone_repo step")
    
    def _get_ordered_steps(self, steps: List[str]) -> List[str]:
        """Get build steps in the correct execution order."""
        step_info = {
            step: self.AVAILABLE_BUILD_STEPS[step]['order']
            for step in steps
        }
        
        # Sort by order, then by name for consistency
        return sorted(steps, key=lambda s: (step_info[s], s))
    
    def _get_repository_info(self, repo_dir: Path) -> Dict[str, str]:
        """Get information about the cloned repository."""
        try:
            # Get current commit hash
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_dir,
                capture_output=True,
                text=True
            )
            
            commit_hash = result.stdout.strip() if result.returncode == 0 else 'unknown'
            
            # Get remote URL
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=repo_dir,
                capture_output=True,
                text=True
            )
            
            remote_url = result.stdout.strip() if result.returncode == 0 else 'unknown'
            
            # Get current branch
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=repo_dir,
                capture_output=True,
                text=True
            )
            
            current_branch = result.stdout.strip() if result.returncode == 0 else 'unknown'
            
            return {
                'commit_hash': commit_hash,
                'remote_url': remote_url,
                'current_branch': current_branch
            }
            
        except Exception as e:
            logger.warning(f"Failed to get repository info: {str(e)}")
            return {
                'commit_hash': 'unknown',
                'remote_url': 'unknown',
                'current_branch': 'unknown'
            }
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        import hashlib
        
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            return sha256_hash.hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to calculate checksum: {str(e)}")
            return 'unknown'
    
    def _get_build_outputs(self, pipeline_run: PipelineRun) -> List[BuildOutput]:
        """Get all build outputs for a pipeline run."""
        return self.db.query(BuildOutput).filter(
            BuildOutput.pipeline_run_id == pipeline_run.id
        ).all()
    
    def get_pipeline_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get pipeline execution statistics.
        
        Args:
            days: Number of days to look back for statistics
            
        Returns:
            Dictionary with pipeline statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get pipeline runs in the time period
            runs = self.db.query(PipelineRun).filter(
                PipelineRun.started_at >= cutoff_date
            ).all()
            
            # Calculate statistics
            total_runs = len(runs)
            completed_runs = len([r for r in runs if r.status == 'completed'])
            failed_runs = len([r for r in runs if r.status == 'failed'])
            pending_runs = len([r for r in runs if r.status == 'pending'])
            running_runs = len([r for r in runs if r.status == 'running'])
            
            # Calculate success rate
            success_rate = (completed_runs / total_runs * 100) if total_runs > 0 else 0
            
            # Get popular steps
            step_counts = {}
            for run in runs:
                if run.steps_to_execute:
                    for step in run.steps_to_execute:
                        step_counts[step] = step_counts.get(step, 0) + 1
            
            return {
                'period_days': days,
                'total_runs': total_runs,
                'completed_runs': completed_runs,
                'failed_runs': failed_runs,
                'pending_runs': pending_runs,
                'running_runs': running_runs,
                'success_rate_percent': round(success_rate, 2),
                'popular_steps': sorted(step_counts.items(), key=lambda x: x[1], reverse=True),
                'date_range': {
                    'start': cutoff_date.isoformat(),
                    'end': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting pipeline statistics: {str(e)}")
            return {
                'period_days': days,
                'total_runs': 0,
                'completed_runs': 0,
                'failed_runs': 0,
                'pending_runs': 0,
                'running_runs': 0,
                'success_rate_percent': 0,
                'popular_steps': [],
                'error': str(e)
            }
    
    def get_repository_usage(self, repository_id: int) -> Dict[str, Any]:
        """
        Get usage statistics for a specific repository.
        
        Args:
            repository_id: Repository ID to analyze
            
        Returns:
            Dictionary with repository usage statistics
        """
        try:
            # Get repository
            repository = self.db.query(GitRepository).filter(
                GitRepository.id == repository_id
            ).first()
            
            if not repository:
                raise NotFoundError(f"Repository with ID {repository_id} not found")
            
            # Get pipeline runs for this repository
            runs = self.db.query(PipelineRun).filter(
                PipelineRun.git_repository_id == repository_id
            ).all()
            
            # Calculate statistics
            total_runs = len(runs)
            completed_runs = len([r for r in runs if r.status == 'completed'])
            failed_runs = len([r for r in runs if r.status == 'failed'])
            
            # Get recent activity (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_runs = len([r for r in runs if r.started_at >= thirty_days_ago])
            
            # Get build outputs
            outputs = self.db.query(BuildOutput).join(PipelineRun).filter(
                PipelineRun.git_repository_id == repository_id
            ).all()
            
            total_outputs = len(outputs)
            zip_outputs = len([o for o in outputs if o.output_type == 'zip'])
            docker_outputs = len([o for o in outputs if o.output_type == 'docker_image'])
            
            return {
                'repository_id': repository_id,
                'repository_name': repository.name,
                'repository_url': repository.repository_url,
                'is_verified': repository.is_verified,
                'total_pipeline_runs': total_runs,
                'completed_runs': completed_runs,
                'failed_runs': failed_runs,
                'recent_runs_30_days': recent_runs,
                'total_build_outputs': total_outputs,
                'zip_outputs': zip_outputs,
                'docker_outputs': docker_outputs,
                'last_used': max([r.started_at for r in runs]).isoformat() if runs else None
            }
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting repository usage: {str(e)}")
            raise DatabaseError(f"Failed to get repository usage: {str(e)}")
    
    def cleanup_expired_outputs(self) -> Dict[str, Any]:
        """
        Clean up expired build outputs.
        
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            now = datetime.utcnow()
            
            # Find expired outputs
            expired_outputs = self.db.query(BuildOutput).filter(
                BuildOutput.expires_at.isnot(None),
                BuildOutput.expires_at < now
            ).all()
            
            cleaned_count = 0
            cleaned_size = 0
            
            for output in expired_outputs:
                try:
                    # Delete file if it exists
                    if output.file_path and Path(output.file_path).exists():
                        file_size = Path(output.file_path).stat().st_size
                        Path(output.file_path).unlink()
                        cleaned_size += file_size
                    
                    # Delete database record
                    self.db.delete(output)
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to clean up output {output.id}: {str(e)}")
            
            if cleaned_count > 0:
                self.db.commit()
            
            return {
                'cleaned_count': cleaned_count,
                'cleaned_size_bytes': cleaned_size,
                'cleaned_size_mb': round(cleaned_size / (1024 * 1024), 2),
                'timestamp': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise DatabaseError(f"Cleanup failed: {str(e)}")
    
    def get_pipeline_logs(self, run_id: int) -> str:
        """
        Get the logs for a pipeline run.
        
        Args:
            run_id: Pipeline run ID
            
        Returns:
            Log content as string
            
        Raises:
            NotFoundError: If pipeline run doesn't exist
        """
        try:
            pipeline_run = self.db.query(PipelineRun).filter(
                PipelineRun.id == run_id
            ).first()
            
            if not pipeline_run:
                raise NotFoundError(f"Pipeline run with ID {run_id} not found")
            
            return pipeline_run.logs or "No logs available"
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting pipeline logs: {str(e)}")
            raise DatabaseError(f"Failed to get logs: {str(e)}")
    
    def download_build_output(self, output_id: int) -> str:
        """
        Get the file path for downloading a build output.
        
        Args:
            output_id: Build output ID
            
        Returns:
            File path for download
            
        Raises:
            NotFoundError: If build output doesn't exist
            FileOperationError: If file doesn't exist
        """
        try:
            output = self.db.query(BuildOutput).filter(
                BuildOutput.id == output_id
            ).first()
            
            if not output:
                raise NotFoundError(f"Build output with ID {output_id} not found")
            
            if not output.file_path:
                raise FileOperationError("No file available for download")
            
            file_path = Path(output.file_path)
            if not file_path.exists():
                raise FileOperationError(f"File not found: {output.file_path}")
            
            return str(file_path)
            
        except (NotFoundError, FileOperationError):
            raise
        except Exception as e:
            logger.error(f"Error downloading build output: {str(e)}")
            raise DatabaseError(f"Download failed: {str(e)}")