from sqlalchemy.orm import Session
from app.models.models import BrandingTemplate, BrandingAsset
from app.schemas.branding import BrandingTemplateCreate, BrandingTemplateUpdate, BrandingAssetCreate
from typing import List, Optional
import os
import shutil

def get_branding_template(db: Session, template_id: int) -> Optional[BrandingTemplate]:
    return db.query(BrandingTemplate).filter(BrandingTemplate.id == template_id).first()

def get_branding_template_by_name(db: Session, name: str) -> Optional[BrandingTemplate]:
    return db.query(BrandingTemplate).filter(BrandingTemplate.name == name).first()

def get_branding_templates(db: Session, skip: int = 0, limit: int = 100) -> List[BrandingTemplate]:
    return db.query(BrandingTemplate).offset(skip).limit(limit).all()

def create_branding_template(db: Session, template: BrandingTemplateCreate) -> BrandingTemplate:
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

def update_branding_template(db: Session, template_id: int, template: BrandingTemplateUpdate) -> Optional[BrandingTemplate]:
    db_template = get_branding_template(db, template_id)
    if db_template:
        update_data = template.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_template, key, value)
        db.commit()
        db.refresh(db_template)
    return db_template

def delete_branding_template(db: Session, template_id: int) -> bool:
    db_template = get_branding_template(db, template_id)
    if db_template:
        # Delete associated assets first
        db.query(BrandingAsset).filter(BrandingAsset.template_id == template_id).delete()
        
        # Delete the template
        db.delete(db_template)
        db.commit()
        return True
    return False

def get_branding_assets(db: Session, template_id: int) -> List[BrandingAsset]:
    return db.query(BrandingAsset).filter(BrandingAsset.template_id == template_id).all()

def create_branding_asset(db: Session, asset: BrandingAssetCreate) -> BrandingAsset:
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

def delete_branding_asset(db: Session, asset_id: int) -> bool:
    db_asset = db.query(BrandingAsset).filter(BrandingAsset.id == asset_id).first()
    if db_asset:
        # Delete the file from disk if it exists
        if os.path.exists(db_asset.file_path):
            os.remove(db_asset.file_path)
        
        # Delete the asset from database
        db.delete(db_asset)
        db.commit()
        return True
    return False

def get_branding_asset_by_filename(db: Session, template_id: int, filename: str) -> Optional[BrandingAsset]:
    return db.query(BrandingAsset).filter(
        BrandingAsset.template_id == template_id,
        BrandingAsset.file_name == filename
    ).first()

def update_branding_asset(db: Session, asset_id: int, file_name: str, file_type: str, file_path: str) -> Optional[BrandingAsset]:
    db_asset = db.query(BrandingAsset).filter(BrandingAsset.id == asset_id).first()
    if db_asset:
        db_asset.file_name = file_name
        db_asset.file_type = file_type
        db_asset.file_path = file_path
        db.commit()
        db.refresh(db_asset)
    return db_asset