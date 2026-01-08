"""
Main FastAPI application for the Open WebUI Customizer.

This module initializes and configures the FastAPI application with all
necessary components including routing, middleware, static files, and
database connections.
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Add the parent directory to the path for proper imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.config import get_settings
from app.utils.logging import setup_logging
from app.models.database import init_database, engine, Base, SessionLocal
from app.api.branding import router as branding_router
from app.api.configuration import router as config_router
from app.api.registry import router as registry_router
from app.api.pipeline import router as pipeline_router
from app.api.credential import router as credential_router
from app.api.git_repository import router as git_repo_router
from app.api.enhanced_pipeline import router as enhanced_pipeline_router
from app.services.branding import get_branding_templates
from app.services.registry import get_all_registries
from app.services.pipeline import get_all_pipeline_runs, get_pipeline_run

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with database initialization."""
    # Get settings and configure logging
    settings = get_settings()
    
    # Setup logging based on environment
    setup_logging(settings.logging.log_level, settings.logging.log_file)
    
    # Initialize database (tables are handled in database.py based on environment)
    await startup_db()
    
    yield
    
    # Shutdown cleanup
    await cleanup_db()

async def startup_db():
    """Initialize database on startup."""
    settings = get_settings()
    
    print(f"Starting Open WebUI Customizer in {settings.environment} mode")
    print(f"Debug mode: {settings.debug}")
    print(f"Auto-create tables: {getattr(settings.database, 'auto_create_tables', 'N/A')}")
    print(f"Database URL: {settings.database.database_url}")
    
    # Database initialization is now handled in models/database.py
    # based on the auto_create_tables setting

async def cleanup_db():
    """Cleanup database connections on shutdown."""
    # Dispose of the database engine
    engine.dispose()
    print("Database connections closed")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Open WebUI Customizer",
    description="API for customizing Open WebUI with custom branding and builds",
    version="1.0.0",
    lifespan=lifespan,
    debug=get_settings().debug
)

# Configure CORS based on environment settings
cors_settings = get_settings().security.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_settings,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(branding_router)
app.include_router(config_router)
app.include_router(registry_router)
app.include_router(pipeline_router)
app.include_router(credential_router)
app.include_router(git_repo_router)
app.include_router(enhanced_pipeline_router)

# Mount static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount customization directory for serving branding assets
customization_dir = os.path.join(os.path.dirname(__file__), "..", "customization")
if os.path.exists(customization_dir):
    app.mount("/customization", StaticFiles(directory=customization_dir), name="customization")

# Set up templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
templates = Jinja2Templates(directory=templates_dir)

# Dependency to get DB session
def get_db():
    """FastAPI dependency to get database session."""
    from app.models.database import get_db as get_db_session
    return get_db_session()

# UI Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/branding", response_class=HTMLResponse)
async def branding_page(request: Request, db: Session = Depends(get_db)):
    templates_list = get_branding_templates(db)
    return templates.TemplateResponse("branding.html", {"request": request, "templates": templates_list})

@app.get("/branding/create", response_class=HTMLResponse)
async def create_branding_template(request: Request):
    return templates.TemplateResponse("create_template.html", {"request": request})

@app.get("/branding/{template_id}/edit", response_class=HTMLResponse)
async def edit_branding_template(request: Request, template_id: int, db: Session = Depends(get_db)):
    from services.branding import get_branding_template
    template = get_branding_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return templates.TemplateResponse("edit_template.html", {"request": request, "template": template})

@app.get("/branding/{template_id}/assets", response_class=HTMLResponse)
async def manage_branding_assets(request: Request, template_id: int, db: Session = Depends(get_db)):
    from services.branding import get_branding_template, get_branding_assets
    template = get_branding_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    assets = get_branding_assets(db, template_id)
    return templates.TemplateResponse("manage_assets.html", {"request": request, "template": template, "assets": assets})

@app.get("/configuration", response_class=HTMLResponse)
async def configuration_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("configuration.html", {"request": request})

@app.get("/enhanced-pipeline", response_class=HTMLResponse)
async def enhanced_pipeline_page(request: Request, db: Session = Depends(get_db)):
    """Render the enhanced pipeline page with custom fork cloning support."""
    return templates.TemplateResponse("enhanced_pipeline.html", {"request": request})

@app.get("/repositories", response_class=HTMLResponse)
async def repositories_page(request: Request, db: Session = Depends(get_db)):
    """Render the Git repositories management page."""
    return templates.TemplateResponse("repositories.html", {"request": request})

@app.get("/credentials", response_class=HTMLResponse)
async def credentials_page(request: Request, db: Session = Depends(get_db)):
    """Render the credentials management page."""
    return templates.TemplateResponse("credentials.html", {"request": request})

@app.get("/replacement-tool", response_class=HTMLResponse)
async def replacement_tool_page(request: Request):
    return templates.TemplateResponse("replacement_tool.html", {"request": request})

@app.get("/configuration/create", response_class=HTMLResponse)
async def create_configuration(request: Request):
    return templates.TemplateResponse("create_config.html", {"request": request})

@app.get("/configuration/{config_id}/edit", response_class=HTMLResponse)
async def edit_configuration(request: Request, config_id: int, db: Session = Depends(get_db)):
    from services.configuration import get_configuration
    config = get_configuration(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return templates.TemplateResponse("edit_config.html", {"request": request, "config": config})

@app.get("/pipeline", response_class=HTMLResponse)
async def pipeline_page(request: Request, db: Session = Depends(get_db)):
    templates_list = get_branding_templates(db)
    registries_list = get_all_registries(db)
    return templates.TemplateResponse("pipeline.html", {
        "request": request,
        "templates": templates_list,
        "registries": registries_list
    })

@app.get("/pipeline/runs/{run_id}/logs", response_class=HTMLResponse)
async def pipeline_logs(request: Request, run_id: int, db: Session = Depends(get_db)):
    run = get_pipeline_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return templates.TemplateResponse("pipeline_logs.html", {"request": request, "run": run})

@app.get("/registries/create", response_class=HTMLResponse)
async def create_registry(request: Request):
    return templates.TemplateResponse("create_registry.html", {"request": request})

@app.get("/registries/{registry_id}/edit", response_class=HTMLResponse)
async def edit_registry(request: Request, registry_id: int, db: Session = Depends(get_db)):
    from services.registry import get_registry
    registry = get_registry(db, registry_id)
    if not registry:
        raise HTTPException(status_code=404, detail="Registry not found")
    return templates.TemplateResponse("edit_registry.html", {"request": request, "registry": registry})

# API Routes for UI
@app.get("/api/v1/branding/templates", response_class=HTMLResponse)
async def api_branding_templates(request: Request, db: Session = Depends(get_db)):
    templates_list = get_branding_templates(db)
    return templates.TemplateResponse("template_list.html", {"request": request, "templates": templates_list})

@app.get("/api/v1/registries/", response_class=HTMLResponse)
async def api_registries(request: Request, db: Session = Depends(get_db)):
    registries_list = get_all_registries(db)
    return templates.TemplateResponse("registry_list.html", {"request": request, "registries": registries_list})

@app.get("/api/v1/configuration/", response_class=HTMLResponse)
async def api_configurations(request: Request, db: Session = Depends(get_db)):
    from services.configuration import get_all_configurations
    configs_list = get_all_configurations(db)
    return templates.TemplateResponse("config_list.html", {"request": request, "configs": configs_list})

@app.get("/api/v1/pipeline/runs", response_class=HTMLResponse)
async def api_pipeline_runs(request: Request, db: Session = Depends(get_db)):
    runs_list = get_all_pipeline_runs(db)
    return templates.TemplateResponse("pipeline_runs.html", {"request": request, "runs": runs_list})

@app.get("/api/v1/branding/files", response_class=HTMLResponse)
async def api_branding_files(request: Request, db: Session = Depends(get_db)):
    from app.api.branding import get_all_branding_files
    files_list = get_all_branding_files(db)
    return templates.TemplateResponse("file_list.html", {"request": request, "files": files_list})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)