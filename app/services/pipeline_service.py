import json
import os
import subprocess
import re
from pathlib import Path
from sqlalchemy.orm import Session
from app.models import models
from app.schemas import branding
from app.services.registry_service import RegistryService
from app.services.branding import get_branding_template

class PipelineService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_pipeline_steps(self):
        """Get all available pipeline steps"""
        return [
            {"name": "clone", "description": "Clone/fetch the latest Open WebUI code"},
            {"name": "branding", "description": "Apply branding customizations (text replacements)"},
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
                elif step == "branding":
                    log_output += self._execute_branding_step(template_id)
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

    def _execute_branding_step(self, template_id: int):
        """Execute the branding step - apply text replacements to Open WebUI source"""
        log_output = "\n=== Branding Step ===\n"

        # Get the branding template
        template = get_branding_template(self.db, template_id)
        if not template:
            log_output += "Warning: Branding template not found\n"
            return log_output

        log_output += f"Applying branding template: {template.name}\n"

        # Check if open-webui directory exists
        openwebui_dir = Path("open-webui")
        if not openwebui_dir.exists():
            log_output += "Error: Open WebUI source directory not found. Run clone step first.\n"
            return log_output

        # Apply replacement rules
        replacement_rules = template.replacement_rules or []
        if not replacement_rules:
            log_output += "No replacement rules found in template\n"
            return log_output

        log_output += f"Applying {len(replacement_rules)} replacement rules...\n"

        files_modified = 0
        replacements_made = 0

        # File extensions to process for text replacements
        text_extensions = {'.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.json', '.md', '.txt', '.py'}

        # Walk through all files in open-webui directory
        for file_path in openwebui_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in text_extensions:
                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    original_content = content
                    file_modified = False

                    # Apply each replacement rule
                    for rule in replacement_rules:
                        pattern = rule.get('pattern', '')
                        replacement = rule.get('replacement', '')
                        use_regex = rule.get('use_regex', False)

                        if not pattern:
                            continue

                        if use_regex:
                            try:
                                # Use regex replacement
                                new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
                                if new_content != content:
                                    replacements_made += len(re.findall(pattern, content, re.MULTILINE | re.DOTALL))
                                    content = new_content
                                    file_modified = True
                            except re.error as e:
                                log_output += f"Warning: Invalid regex pattern '{pattern}': {e}\n"
                        else:
                            # Use simple string replacement
                            if pattern in content:
                                count = content.count(pattern)
                                replacements_made += count
                                content = content.replace(pattern, replacement)
                                file_modified = True

                    # Write back if modified
                    if file_modified:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        files_modified += 1
                        rel_path = file_path.relative_to(openwebui_dir)
                        log_output += f"Modified: {rel_path}\n"

                except Exception as e:
                    rel_path = file_path.relative_to(openwebui_dir)
                    log_output += f"Error processing {rel_path}: {str(e)}\n"

        log_output += f"Branding step completed: {files_modified} files modified, {replacements_made} replacements made\n"

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