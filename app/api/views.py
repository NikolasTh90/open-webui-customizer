from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request):
    """Serve the templates management page"""
    return templates.TemplateResponse("templates.html", {"request": request})

@router.get("/templates/new", response_class=HTMLResponse)
async def new_template_form(request: Request):
    """Serve the new template form"""
    return templates.TemplateResponse("template_editor.html", {"request": request})

@router.get("/assets", response_class=HTMLResponse)
async def assets_page(request: Request):
    """Serve the assets management page"""
    return templates.TemplateResponse("assets.html", {"request": request})

@router.get("/assets/upload-form", response_class=HTMLResponse)
async def asset_upload_form(request: Request):
    """Serve the asset upload form"""
    return templates.TemplateResponse("asset_upload.html", {"request": request})

@router.get("/registry", response_class=HTMLResponse)
async def registry_page(request: Request):
    """Serve the registry management page"""
    return templates.TemplateResponse("registry.html", {"request": request})

@router.get("/registry/new", response_class=HTMLResponse)
async def new_registry_form(request: Request):
    """Serve the new registry form"""
    return templates.TemplateResponse("registry_editor.html", {"request": request})

@router.get("/pipeline", response_class=HTMLResponse)
async def pipeline_page(request: Request):
    """Serve the pipeline management page"""
    return templates.TemplateResponse("pipeline.html", {"request": request})