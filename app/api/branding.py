from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.branding import BrandingTemplate, BrandingTemplateCreate, BrandingTemplateUpdate, BrandingAsset
from app.services.branding import (
    get_branding_template, get_branding_templates, create_branding_template,
    update_branding_template, delete_branding_template, get_branding_assets,
    create_branding_asset, delete_branding_asset, get_branding_asset_by_filename,
    update_branding_asset, get_branding_template_by_name
)
from typing import List, Optional
import os
import shutil
import json
from pathlib import Path

router = APIRouter(prefix="/api/v1/branding", tags=["branding"])

# Directory for storing uploaded branding assets
UPLOAD_DIR = Path("customization/static")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/templates", response_model=List[BrandingTemplate])
def read_branding_templates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    templates = get_branding_templates(db, skip=skip, limit=limit)
    return templates

@router.get("/templates/{template_id}", response_model=BrandingTemplate)
def read_branding_template(template_id: int, db: Session = Depends(get_db)):
    db_template = get_branding_template(db, template_id)
    if db_template is None:
        raise HTTPException(status_code=404, detail="Branding template not found")
    return db_template

@router.post("/templates", response_model=BrandingTemplate)
def create_new_branding_template(template: BrandingTemplateCreate, db: Session = Depends(get_db)):
    db_template = get_branding_template_by_name(db, template.name)
    if db_template:
        raise HTTPException(status_code=400, detail="Branding template with this name already exists")
    return create_branding_template(db, template)

@router.put("/templates/{template_id}", response_model=BrandingTemplate)
def update_existing_branding_template(template_id: int, template: BrandingTemplateUpdate, db: Session = Depends(get_db)):
    db_template = update_branding_template(db, template_id, template)
    if db_template is None:
        raise HTTPException(status_code=404, detail="Branding template not found")
    return db_template

@router.delete("/templates/{template_id}")
def delete_existing_branding_template(template_id: int, db: Session = Depends(get_db)):
    success = delete_branding_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Branding template not found")
    return {"message": "Branding template deleted successfully"}

@router.get("/templates/{template_id}/assets", response_model=List[BrandingAsset])
def read_branding_assets(template_id: int, db: Session = Depends(get_db)):
    return get_branding_assets(db, template_id)

@router.post("/upload")
async def upload_branding_asset(
    template_id: int = Form(...),
    file: UploadFile = File(...),
    file_type: str = Form(...),
    db: Session = Depends(get_db)
):
    # Validate that the template exists
    db_template = get_branding_template(db, template_id)
    if db_template is None:
        raise HTTPException(status_code=404, detail="Branding template not found")
    
    # Create directory for this template if it doesn't exist
    template_dir = UPLOAD_DIR / f"template_{template_id}"
    template_dir.mkdir(exist_ok=True)
    
    # Save file to disk
    file_path = template_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Check if asset already exists
    db_asset = get_branding_asset_by_filename(db, template_id, file.filename)
    if db_asset:
        # Update existing asset
        updated_asset = update_branding_asset(db, db_asset.id, file.filename, file_type, str(file_path))
        return {"message": "File updated successfully", "asset": updated_asset}
    else:
        # Create new asset
        new_asset = create_branding_asset(db, BrandingAssetCreate(
            template_id=template_id,
            file_name=file.filename,
            file_type=file_type,
            file_path=str(file_path)
        ))
        return {"message": "File uploaded successfully", "asset": new_asset}

@router.delete("/assets/{asset_id}")
def delete_branding_asset_endpoint(asset_id: int, db: Session = Depends(get_db)):
    success = delete_branding_asset(db, asset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Branding asset not found")
    return {"message": "Branding asset deleted successfully"}

@router.get("/templates/{template_id}/export")
def export_branding_template(template_id: int, db: Session = Depends(get_db)):
    db_template = get_branding_template(db, template_id)
    if db_template is None:
        raise HTTPException(status_code=404, detail="Branding template not found")
    
    # Get associated assets
    assets = get_branding_assets(db, template_id)
    
    # Create export data
    export_data = {
        "template": {
            "name": db_template.name,
            "description": db_template.description,
            "brand_name": db_template.brand_name,
            "replacement_rules": db_template.replacement_rules
        },
        "assets": [
            {
                "file_name": asset.file_name,
                "file_type": asset.file_type,
                "file_path": asset.file_path
            }
            for asset in assets
        ]
    }
    
    return export_data

@router.post("/templates/import")
def import_branding_template(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # Read the uploaded file content
        content = file.file.read()
        import_data = json.loads(content)
        
        # Validate data
        if "template" not in import_data:
            raise HTTPException(status_code=400, detail="Invalid template data format")
        
        # Check if template with same name already exists
        template_data = import_data["template"]
        existing_template = get_branding_template_by_name(db, template_data["name"])
        if existing_template:
            raise HTTPException(status_code=400, detail=f"Template with name '{template_data['name']}' already exists")
        
        # Create the new template
        new_template = create_branding_template(db, BrandingTemplateCreate(**template_data))
        
        return {"message": "Template imported successfully", "template_id": new_template.id}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importing template: {str(e)}")