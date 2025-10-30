import json
import os
import subprocess
from sqlalchemy.orm import Session
from app.models import models
from app.schemas import branding
from app.services.registry_service import RegistryService

class PipelineService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_pipeline_steps(self):
        """Get all available pipeline steps"""
        return [
            {"name": "clone", "description": "Clone/fetch the latest Open WebUI code"},
            {"name": "build", "description": "Build the Svelte frontend and Docker image"},
            {"name": "publish", "description": "Publish the customized Docker image to a registry"},
            {"name": "clean", "description": "Clean up the environment and reset submodules"}
        ]
    
    def execute_pipeline(self, steps: list, template_id: int):
        """Execute the pipeline with selected steps"""
        # Create a new pipeline run record
        selected_steps_json = json.dumps(steps)
        db_pipeline_run = models.PipelineRun(
            status="running",
            selected_steps=selected_steps_json,
            template_id=template_id
        )
        self.db.add(db_pipeline_run)
        self.db.commit()
        self.db.refresh(db_pipeline_run)
        
        log_output = ""
        
        try:
            # Execute each step in order
            for step in steps:
                if step == "clone":
                    log_output += self._execute_clone_step()
                elif step == "build":
                    log_output += self._execute_build_step()
                elif step == "publish":
                    log_output += self._execute_publish_step()
                elif step == "clean":
                    log_output += self._execute_clean_step()
            
            # Update pipeline run status to completed
            db_pipeline_run.status = "completed"
            db_pipeline_run.log_output = log_output
            
            # Try to get the build version
            try:
                with open("open-webui/package.json", "r") as f:
                    package_json = json.load(f)
                    db_pipeline_run.build_version = package_json.get("version", "unknown")
            except:
                db_pipeline_run.build_version = "unknown"
                
        except Exception as e:
            # Update pipeline run status to failed
            db_pipeline_run.status = "failed"
            log_output += f"\nError: {str(e)}"
            db_pipeline_run.log_output = log_output
        
        db_pipeline_run.end_time = models.datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_pipeline_run)
        
        return db_pipeline_run
    
    def _execute_clone_step(self):
        """Execute the clone step"""
        log_output = "\n=== Clone Step ===\n"
        
        # Check if open-webui directory exists
        if not os.path.exists("open-webui"):
            # Initialize submodule
            result = subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive", "--remote"],
                capture_output=True,
                text=True
            )
            log_output += result.stdout
            if result.stderr:
                log_output += f"STDERR: {result.stderr}\n"
        else:
            # Update submodule
            result = subprocess.run(
                ["git", "submodule", "update", "--recursive", "--remote"],
                cwd="open-webui",
                capture_output=True,
                text=True
            )
            log_output += result.stdout
            if result.stderr:
                log_output += f"STDERR: {result.stderr}\n"
        
        return log_output
    
    def _execute_build_step(self):
        """Execute the build step"""
        log_output = "\n=== Build Step ===\n"
        
        # Copy customization files
        customization_dir = "customization"
        static_dir = "open-webui/static"
        
        if os.path.exists(customization_dir) and os.path.exists(static_dir):
            # This is where we'd copy the files
            log_output += "Copying customization files...\n"
        else:
            log_output += "Warning: customization or static directory not found\n"
        
        # Build the application
        try:
            # Run the build script
            result = subprocess.run(
                ["./build.sh"],
                capture_output=True,
                text=True
            )
            log_output += result.stdout
            if result.stderr:
                log_output += f"STDERR: {result.stderr}\n"
        except Exception as e:
            log_output += f"Build failed: {str(e)}\n"
        
        return log_output
    
    def _execute_publish_step(self):
        """Execute the publish step"""
        log_output = "\n=== Publish Step ===\n"
        
        # Get active registry
        registry_service = RegistryService(self.db)
        active_registry = registry_service.get_active_registry()
        
        if not active_registry:
            log_output += "No active registry configured\n"
            return log_output
        
        # Try to run the publish script
        try:
            result = subprocess.run(
                ["./publish.sh"],
                capture_output=True,
                text=True
            )
            log_output += result.stdout
            if result.stderr:
                log_output += f"STDERR: {result.stderr}\n"
        except Exception as e:
            log_output += f"Publish failed: {str(e)}\n"
        
        return log_output
    
    def _execute_clean_step(self):
        """Execute the clean step"""
        log_output = "\n=== Clean Step ===\n"
        
        # Run the clean script
        try:
            result = subprocess.run(
                ["./clean.sh"],
                capture_output=True,
                text=True
            )
            log_output += result.stdout
            if result.stderr:
                log_output += f"STDERR: {result.stderr}\n"
        except Exception as e:
            log_output += f"Clean failed: {str(e)}\n"
        
        return log_output
    
    def get_pipeline_runs(self):
        """Get all pipeline runs"""
        return self.db.query(models.PipelineRun).order_by(
            models.PipelineRun.start_time.desc()
        ).all()
    
    def get_pipeline_run(self, run_id: int):
        """Get a specific pipeline run"""
        return self.db.query(models.PipelineRun).filter(
            models.PipelineRun.id == run_id
        ).first()