from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.branding import PipelineRun, BrandingTemplate
from app.services.dashboard_service import DashboardService
from app.services.pipeline_service import PipelineService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/api")
async def get_dashboard_data(db: Session = Depends(get_db)):
    """Get dashboard data including pipeline status and build history"""
    dashboard_service = DashboardService(db)
    try:
        data = dashboard_service.get_dashboard_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/metrics")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """Get performance metrics for builds"""
    dashboard_service = DashboardService(db)
    try:
        metrics = dashboard_service.get_performance_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/pipeline/steps")
async def get_pipeline_steps():
    """Get available pipeline steps"""
    pipeline_service = PipelineService(None)
    return {"steps": pipeline_service.get_pipeline_steps()}