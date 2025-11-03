"""
Branding service for managing branding templates and assets.

This module provides business logic for creating, updating, and managing
branding templates and their associated assets. It handles database
operations and file system interactions for branding resources.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.config import get_settings
from app.exceptions import (
    NotFoundError,
    ValidationError,
    FileOperationError,
    BrandingError,
    DatabaseError
)
from app.models.models import BrandingTemplate, BrandingAsset
from app.schemas.branding import (
    BrandingTemplateCreate,
    BrandingTemplateUpdate,
    BrandingAssetCreate
)
from app.utils.logging import LoggerMixin

def get_branding_template(db: Session, template_id: int) -> Optional[BrandingTemplate]:
    """
    Retrieve a branding template by its ID.

    Args:
        db: Database session.
        template_id: Unique identifier of the branding template.

    Returns:
        Optional[BrandingTemplate]: The branding template if found, None otherwise.

    Raises:
        DatabaseError: If there's an issue with the database query.
    """
    try:
        return db.query(BrandingTemplate).filter(BrandingTemplate.id == template_id).first()
    except Exception as e:
        raise DatabaseError(
            f"Failed to retrieve branding template {template_id}",
            operation="select",
            table="branding_templates",
            details={"template_id": template_id, "error": str(e)}
        )

def get_branding_template_by_name(db: Session, name: str) -> Optional[BrandingTemplate]:
    """
    Retrieve a branding template by its name.

    Args:
        db: Database session.
        name: Name of the branding template.

    Returns:
        Optional[BrandingTemplate]: The branding template if found, None otherwise.

    Raises:
        DatabaseError: If there's an issue with the database query.
    """
    try:
        return db.query(BrandingTemplate).filter(BrandingTemplate.name == name).first()
    except Exception as e:
        raise DatabaseError(
            f"Failed to retrieve branding template by name '{name}'",
            operation="select",
            table="branding_templates",
            details={"name": name, "error": str(e)}
        )

def get_branding_templates(db: Session, skip: int = 0, limit: int = 100) -> List[BrandingTemplate]:
    """
    Retrieve a list of branding templates with pagination.

    Args:
        db: Database session.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        List[BrandingTemplate]: List of branding templates.

    Raises:
        DatabaseError: If there's an issue with the database query.
    """
    try:
        return db.query(BrandingTemplate).offset(skip).limit(limit).all()
    except Exception as e:
        raise DatabaseError(
            f"Failed to retrieve branding templates (skip={skip}, limit={limit})",
            operation="select",
            table="branding_templates",
            details={"skip": skip, "limit": limit, "error": str(e)}
        )

def create_branding_template(db: Session, template: BrandingTemplateCreate) -> BrandingTemplate:
    """
    Create a new branding template.

    Args:
        db: Database session.
        template: Branding template creation data.

    Returns:
        BrandingTemplate: The created branding template.

    Raises:
        ValidationError: If the template data is invalid.
        DatabaseError: If there's an issue with the database operation.
    """
    try:
        # Validate replacement rules count
        settings = get_settings()
        if len(template.replacement_rules or []) > settings.branding.max_replacement_rules:
            raise ValidationError(
                f"Too many replacement rules. Maximum allowed: {settings.branding.max_replacement_rules}",
                details={
                    "max_rules": settings.branding.max_replacement_rules,
                    "provided_rules": len(template.replacement_rules or [])
                }
            )

        db_template = BrandingTemplate(
            name=template.name,
            description=template.description,
            brand_name=template.brand_name,
            replacement_rules=template.replacement_rules
        )
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        return db_template
    except ValidationError:
        raise
    except Exception as e:
        db.rollback()
        raise DatabaseError(
            f"Failed to create branding template '{template.name}'",
            operation="insert",
            table="branding_templates",
            details={"template_name": template.name, "error": str(e)}
        )

def update_branding_template(db: Session, template_id: int, template: BrandingTemplateUpdate) -> Optional[BrandingTemplate]:
    """
    Update an existing branding template.

    Args:
        db: Database session.
        template_id: Unique identifier of the branding template to update.
        template: Branding template update data.

    Returns:
        Optional[BrandingTemplate]: The updated branding template if found, None otherwise.

    Raises:
        NotFoundError: If the template doesn't exist.
        ValidationError: If the update data is invalid.
        DatabaseError: If there's an issue with the database operation.
    """
    try:
        db_template = get_branding_template(db, template_id)
        if not db_template:
            raise NotFoundError(
                f"Branding template with ID {template_id} not found",
                details={"template_id": template_id}
            )

        # Validate replacement rules count if provided
        update_data = template.model_dump(exclude_unset=True)
        if "replacement_rules" in update_data:
            settings = get_settings()
            if len(update_data["replacement_rules"]) > settings.branding.max_replacement_rules:
                raise ValidationError(
                    f"Too many replacement rules. Maximum allowed: {settings.branding.max_replacement_rules}",
                    details={
                        "max_rules": settings.branding.max_replacement_rules,
                        "provided_rules": len(update_data["replacement_rules"])
                    }
                )

        for key, value in update_data.items():
            setattr(db_template, key, value)

        db.commit()
        db.refresh(db_template)
        return db_template
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        db.rollback()
        raise DatabaseError(
            f"Failed to update branding template {template_id}",
            operation="update",
            table="branding_templates",
            details={"template_id": template_id, "error": str(e)}
        )

def delete_branding_template(db: Session, template_id: int) -> bool:
    """
    Delete a branding template and all its associated assets.

    Args:
        db: Database session.
        template_id: Unique identifier of the branding template to delete.

    Returns:
        bool: True if the template was deleted, False if it wasn't found.

    Raises:
        DatabaseError: If there's an issue with the database operation.
        FileOperationError: If there's an issue deleting associated files.
    """
    try:
        db_template = get_branding_template(db, template_id)
        if not db_template:
            return False

        # Delete associated assets first
        assets = get_branding_assets(db, template_id)
        for asset in assets:
            try:
                # Delete file from disk if it exists
                asset_path = Path(asset.file_path)
                if asset_path.exists():
                    asset_path.unlink()
            except Exception as e:
                raise FileOperationError(
                    f"Failed to delete asset file for template {template_id}",
                    file_path=str(asset.file_path),
                    operation="delete",
                    details={"asset_id": asset.id, "error": str(e)}
                )

        # Delete assets from database
        db.query(BrandingAsset).filter(BrandingAsset.template_id == template_id).delete()

        # Delete the template
        db.delete(db_template)
        db.commit()
        return True
    except (FileOperationError,):
        raise
    except Exception as e:
        db.rollback()
        raise DatabaseError(
            f"Failed to delete branding template {template_id}",
            operation="delete",
            table="branding_templates",
            details={"template_id": template_id, "error": str(e)}
        )

def get_branding_assets(db: Session, template_id: int) -> List[BrandingAsset]:
    """
    Retrieve all branding assets for a specific template.

    Args:
        db: Database session.
        template_id: Unique identifier of the branding template.

    Returns:
        List[BrandingAsset]: List of branding assets for the template.

    Raises:
        DatabaseError: If there's an issue with the database query.
    """
    try:
        return db.query(BrandingAsset).filter(BrandingAsset.template_id == template_id).all()
    except Exception as e:
        raise DatabaseError(
            f"Failed to retrieve branding assets for template {template_id}",
            operation="select",
            table="branding_assets",
            details={"template_id": template_id, "error": str(e)}
        )

def create_branding_asset(db: Session, asset: BrandingAssetCreate) -> BrandingAsset:
    """
    Create a new branding asset.

    Args:
        db: Database session.
        asset: Branding asset creation data.

    Returns:
        BrandingAsset: The created branding asset.

    Raises:
        ValidationError: If the asset data is invalid.
        DatabaseError: If there's an issue with the database operation.
    """
    try:
        # Validate file type
        settings = get_settings()
        if asset.file_type not in settings.branding.supported_file_types:
            raise ValidationError(
                f"Unsupported file type: {asset.file_type}",
                details={
                    "supported_types": settings.branding.supported_file_types,
                    "provided_type": asset.file_type
                }
            )

        # Validate file path exists
        asset_path = Path(asset.file_path)
        if not asset_path.exists():
            raise ValidationError(
                f"Asset file does not exist: {asset.file_path}",
                details={"file_path": asset.file_path}
            )

        # Validate file size
        file_size = asset_path.stat().st_size
        if file_size > settings.file_storage.max_file_size:
            raise ValidationError(
                f"File too large: {file_size} bytes. Maximum allowed: {settings.file_storage.max_file_size}",
                details={
                    "file_size": file_size,
                    "max_size": settings.file_storage.max_file_size
                }
            )

        db_asset = BrandingAsset(
            template_id=asset.template_id,
            file_name=asset.file_name,
            file_type=asset.file_type,
            file_path=asset.file_path
        )
        db.add(db_asset)
        db.commit()
        db.refresh(db_asset)
        return db_asset
    except ValidationError:
        raise
    except Exception as e:
        db.rollback()
        raise DatabaseError(
            f"Failed to create branding asset '{asset.file_name}'",
            operation="insert",
            table="branding_assets",
            details={"file_name": asset.file_name, "error": str(e)}
        )

def delete_branding_asset(db: Session, asset_id: int) -> bool:
    """
    Delete a branding asset and its associated file.

    Args:
        db: Database session.
        asset_id: Unique identifier of the branding asset to delete.

    Returns:
        bool: True if the asset was deleted, False if it wasn't found.

    Raises:
        DatabaseError: If there's an issue with the database operation.
        FileOperationError: If there's an issue deleting the associated file.
    """
    try:
        db_asset = db.query(BrandingAsset).filter(BrandingAsset.id == asset_id).first()
        if not db_asset:
            return False

        # Delete the file from disk if it exists
        asset_path = Path(db_asset.file_path)
        if asset_path.exists():
            try:
                asset_path.unlink()
            except Exception as e:
                raise FileOperationError(
                    f"Failed to delete asset file",
                    file_path=str(asset_path),
                    operation="delete",
                    details={"asset_id": asset_id, "error": str(e)}
                )

        # Delete the asset from database
        db.delete(db_asset)
        db.commit()
        return True
    except FileOperationError:
        raise
    except Exception as e:
        db.rollback()
        raise DatabaseError(
            f"Failed to delete branding asset {asset_id}",
            operation="delete",
            table="branding_assets",
            details={"asset_id": asset_id, "error": str(e)}
        )

def get_branding_asset_by_filename(db: Session, template_id: int, filename: str) -> Optional[BrandingAsset]:
    """
    Retrieve a branding asset by template ID and filename.

    Args:
        db: Database session.
        template_id: Unique identifier of the branding template.
        filename: Name of the asset file.

    Returns:
        Optional[BrandingAsset]: The branding asset if found, None otherwise.

    Raises:
        DatabaseError: If there's an issue with the database query.
    """
    try:
        return db.query(BrandingAsset).filter(
            BrandingAsset.template_id == template_id,
            BrandingAsset.file_name == filename
        ).first()
    except Exception as e:
        raise DatabaseError(
            f"Failed to retrieve branding asset by filename '{filename}' for template {template_id}",
            operation="select",
            table="branding_assets",
            details={"template_id": template_id, "filename": filename, "error": str(e)}
        )

def update_branding_asset(db: Session, asset_id: int, file_name: str, file_type: str, file_path: str) -> Optional[BrandingAsset]:
    """
    Update an existing branding asset.

    Args:
        db: Database session.
        asset_id: Unique identifier of the branding asset to update.
        file_name: New filename for the asset.
        file_type: New file type for the asset.
        file_path: New file path for the asset.

    Returns:
        Optional[BrandingAsset]: The updated branding asset if found, None otherwise.

    Raises:
        ValidationError: If the update data is invalid.
        DatabaseError: If there's an issue with the database operation.
    """
    try:
        db_asset = db.query(BrandingAsset).filter(BrandingAsset.id == asset_id).first()
        if not db_asset:
            return None

        # Validate file type
        settings = get_settings()
        if file_type not in settings.branding.supported_file_types:
            raise ValidationError(
                f"Unsupported file type: {file_type}",
                details={
                    "supported_types": settings.branding.supported_file_types,
                    "provided_type": file_type
                }
            )

        # Validate file path exists
        asset_path = Path(file_path)
        if not asset_path.exists():
            raise ValidationError(
                f"Asset file does not exist: {file_path}",
                details={"file_path": file_path}
            )

        db_asset.file_name = file_name
        db_asset.file_type = file_type
        db_asset.file_path = file_path
        db.commit()
        db.refresh(db_asset)
        return db_asset
    except ValidationError:
        raise
    except Exception as e:
        db.rollback()
        raise DatabaseError(
            f"Failed to update branding asset {asset_id}",
            operation="update",
            table="branding_assets",
            details={"asset_id": asset_id, "error": str(e)}
        )