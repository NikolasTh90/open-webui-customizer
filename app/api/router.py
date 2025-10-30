from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from app.api import templates, assets, registry, pipeline, dashboard, views

router = APIRouter()

# API routes
router.include_router(templates.router, prefix="/api/templates", tags=["templates"])
router.include_router(assets.router, prefix="/api/assets", tags=["assets"])
router.include_router(registry.router, prefix="/api/registry", tags=["registry"])
router.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
router.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])

# HTML view routes
router.include_router(views.router, tags=["views"])