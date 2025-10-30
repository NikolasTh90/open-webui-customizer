from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.branding import BrandingTemplate, BrandingTemplateCreate
from app.services.template_service import TemplateService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_model=list[BrandingTemplate])
@router.get("/api", response_model=list[BrandingTemplate])
async def list_templates(db: Session = Depends(get_db)):
    """List all branding templates"""
    template_service = TemplateService(db)
    templates_list = template_service.get_templates()
    return templates_list

@router.post("/", response_model=BrandingTemplate)
@router.post("/api", response_model=BrandingTemplate)
async def create_template(template: BrandingTemplateCreate, db: Session = Depends(get_db)):
    """Create a new branding template"""
    template_service = TemplateService(db)
    try:
        created_template = template_service.create_template(template)
        return created_template
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{template_id}", response_model=BrandingTemplate)
async def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get a specific branding template"""
    template_service = TemplateService(db)
    db_template = template_service.get_template(template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    return db_template

@router.put("/{template_id}", response_model=BrandingTemplate)
async def update_template(template_id: int, template: BrandingTemplateCreate, db: Session = Depends(get_db)):
    """Update a specific branding template"""
    template_service = TemplateService(db)
    updated_template = template_service.update_template(template_id, template)
    if not updated_template:
        raise HTTPException(status_code=404, detail="Template not found")
    return updated_template

@router.delete("/{template_id}")
async def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a specific branding template"""
    template_service = TemplateService(db)
    success = template_service.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": f"Template {template_id} deleted successfully"}

@router.get("/new", response_class=HTMLResponse)
async def new_template_form(request: Request):
    """Serve the new template form"""
    return templates.TemplateResponse("template_editor.html", {"request": request})