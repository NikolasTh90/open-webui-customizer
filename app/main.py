from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import os
import sys

# Add the parent directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.models.database import engine, Base, SessionLocal
from app.api.branding import router as branding_router
from app.api.configuration import router as config_router
from app.api.registry import router as registry_router
from app.api.pipeline import router as pipeline_router
from app.services.branding import get_branding_templates
from app.services.registry import get_all_registries
from app.services.pipeline import get_all_pipeline_runs, get_pipeline_run

# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Open WebUI Customizer")

# Include API routers
app.include_router(branding_router)
app.include_router(config_router)
app.include_router(registry_router)
app.include_router(pipeline_router)

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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# UI Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/branding", response_class=HTMLResponse)
async def branding_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("branding.html", {"request": request})

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)