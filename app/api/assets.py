from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.branding import BrandingAsset
from app.services.asset_service import AssetService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_model=list[BrandingAsset])
@router.get("/api", response_model=list[BrandingAsset])
async def list_assets(db: Session = Depends(get_db)):
    """List all branding assets"""
    asset_service = AssetService(db)
    assets = asset_service.get_assets()
    return assets

@router.post("/upload")
@router.post("/api/upload")
async def upload_asset(file: UploadFile = File(...), template_id: int = 0, db: Session = Depends(get_db)):
    """Upload a new branding asset"""
    asset_service = AssetService(db)
    try:
        created_asset = asset_service.upload_asset(file, template_id)
        return {"message": f"Asset {file.filename} uploaded successfully", "asset": created_asset}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{asset_id}", response_model=BrandingAsset)
async def get_asset(asset_id: int, db: Session = Depends(get_db)):
    """Get a specific branding asset"""
    asset_service = AssetService(db)
    db_asset = asset_service.get_asset(asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return db_asset

@router.delete("/{asset_id}")
async def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    """Delete a specific branding asset"""
    asset_service = AssetService(db)
    success = asset_service.delete_asset(asset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": f"Asset {asset_id} deleted successfully"}

@router.get("/validate/{template_id}")
async def validate_assets(template_id: int, db: Session = Depends(get_db)):
    """Validate all required branding assets for a template"""
    asset_service = AssetService(db)
    try:
        validation_result = asset_service.validate_assets(template_id)
        return validation_result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/upload-form", response_class=HTMLResponse)
async def asset_upload_form(request: Request):
    """Serve the asset upload form"""
    return templates.TemplateResponse("asset_upload.html", {"request": request})