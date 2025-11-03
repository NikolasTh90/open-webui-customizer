import re
import os
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.services.branding import get_branding_template, get_branding_assets
from app.services.asset_service import AssetService


class BrandingApplicationService:
    """Service for applying branding customizations independently of the build process"""

    def __init__(self, db: Session):
        self.db = db
        self.asset_service = AssetService(db)

    def apply_branding_template(self, template_id: int, target_directory: str = "open-webui") -> Dict[str, Any]:
        """
        Apply a branding template to a target directory independently of the build process.

        Args:
            template_id: ID of the branding template to apply
            target_directory: Directory to apply branding to (default: "open-webui")

        Returns:
            Dictionary with results of the branding application
        """
        result = {
            "success": False,
            "template_id": template_id,
            "files_modified": 0,
            "replacements_made": 0,
            "assets_copied": 0,
            "errors": []
        }

        # Get the branding template
        template = get_branding_template(self.db, template_id)
        if not template:
            result["errors"].append("Branding template not found")
            return result

        result["template_name"] = template.name

        # Check if target directory exists
        target_path = Path(target_directory)
        if not target_path.exists():
            result["errors"].append(f"Target directory '{target_directory}' not found")
            return result

        try:
            # Apply text replacements
            text_result = self._apply_text_replacements(template, target_path)
            result["files_modified"] = text_result["files_modified"]
            result["replacements_made"] = text_result["replacements_made"]
            result["errors"].extend(text_result["errors"])

            # Copy branding assets
            asset_result = self._copy_branding_assets(template_id, target_path)
            result["assets_copied"] = asset_result["assets_copied"]
            result["errors"].extend(asset_result["errors"])

            result["success"] = len(result["errors"]) == 0

        except Exception as e:
            result["errors"].append(f"Unexpected error: {str(e)}")

        return result

    def _apply_text_replacements(self, template, target_path: Path) -> Dict[str, Any]:
        """Apply text replacement rules to files in the target directory"""
        result = {
            "files_modified": 0,
            "replacements_made": 0,
            "errors": []
        }

        replacement_rules = template.replacement_rules or []
        if not replacement_rules:
            return result

        # File extensions to process for text replacements
        text_extensions = {'.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.json', '.md', '.txt', '.py'}

        # Walk through all files in target directory
        for file_path in target_path.rglob('*'):
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
                                    result["replacements_made"] += len(re.findall(pattern, content, re.MULTILINE | re.DOTALL))
                                    content = new_content
                                    file_modified = True
                            except re.error as e:
                                result["errors"].append(f"Invalid regex pattern '{pattern}': {e}")
                        else:
                            # Use simple string replacement
                            if pattern in content:
                                count = content.count(pattern)
                                result["replacements_made"] += count
                                content = content.replace(pattern, replacement)
                                file_modified = True

                    # Write back if modified
                    if file_modified:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        result["files_modified"] += 1

                except Exception as e:
                    rel_path = file_path.relative_to(target_path)
                    result["errors"].append(f"Error processing {rel_path}: {str(e)}")

        return result

    def _copy_branding_assets(self, template_id: int, target_path: Path) -> Dict[str, Any]:
        """Copy branding assets to the appropriate locations in the target directory"""
        result = {
            "assets_copied": 0,
            "errors": []
        }

        # Get branding assets for the template
        assets = get_branding_assets(self.db, template_id)

        # Ensure static directory exists in target
        static_dir = target_path / "static"
        static_dir.mkdir(exist_ok=True)

        for asset in assets:
            try:
                asset_path = Path(asset.file_path)
                if asset_path.exists():
                    # Determine destination path based on file type
                    if asset.file_type in ['logo', 'favicon']:
                        # Copy to static directory
                        dest_path = static_dir / asset_path.name
                    elif asset.file_type == 'theme':
                        # Copy CSS themes to static directory
                        dest_path = static_dir / asset_path.name
                    elif asset.file_type == 'manifest':
                        # Copy manifest files to static directory
                        dest_path = static_dir / asset_path.name
                    else:
                        # Copy other files to static directory
                        dest_path = static_dir / asset_path.name

                    # Copy the file
                    import shutil
                    shutil.copy2(asset_path, dest_path)
                    result["assets_copied"] += 1
                else:
                    result["errors"].append(f"Asset file not found: {asset.file_path}")

            except Exception as e:
                result["errors"].append(f"Error copying asset {asset.file_name}: {str(e)}")

        return result

    def validate_branding_application(self, template_id: int, target_directory: str = "open-webui") -> Dict[str, Any]:
        """
        Validate that branding has been properly applied to the target directory.

        Args:
            template_id: ID of the branding template
            target_directory: Directory to validate

        Returns:
            Dictionary with validation results
        """
        result = {
            "valid": True,
            "template_id": template_id,
            "checks": []
        }

        template = get_branding_template(self.db, template_id)
        if not template:
            result["valid"] = False
            result["checks"].append({"check": "template_exists", "passed": False, "message": "Template not found"})
            return result

        target_path = Path(target_directory)
        if not target_path.exists():
            result["valid"] = False
            result["checks"].append({"check": "target_directory_exists", "passed": False, "message": "Target directory not found"})
            return result

        # Check text replacements
        replacement_rules = template.replacement_rules or []
        for rule in replacement_rules:
            pattern = rule.get('pattern', '')
            if not pattern:
                continue

            found = False
            text_extensions = {'.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.json', '.md', '.txt', '.py'}

            for file_path in target_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in text_extensions:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                        if rule.get('use_regex', False):
                            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                                found = True
                                break
                        else:
                            if pattern in content:
                                found = True
                                break
                    except:
                        continue

            result["checks"].append({
                "check": "text_replacement",
                "pattern": pattern,
                "passed": found,
                "message": f"Pattern '{pattern}' {'found' if found else 'not found'} in source"
            })

            if not found:
                result["valid"] = False

        # Check asset files
        assets = get_branding_assets(self.db, template_id)
        static_dir = target_path / "static"

        for asset in assets:
            asset_exists = (static_dir / asset.file_name).exists()
            result["checks"].append({
                "check": "asset_file",
                "file": asset.file_name,
                "passed": asset_exists,
                "message": f"Asset file {asset.file_name} {'exists' if asset_exists else 'not found'} in static directory"
            })

            if not asset_exists:
                result["valid"] = False

        return result