from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.registry import ContainerRegistry, ContainerRegistryCreate, ContainerRegistryUpdate
from app.services.registry import (
    get_registry, get_registry_by_name, get_all_registries,
    create_registry, update_registry, delete_registry
)
from typing import List

router = APIRouter(prefix="/api/v1/registries", tags=["registries"])

@router.get("/", response_model=List[ContainerRegistry])
def read_all_registries(db: Session = Depends(get_db)):
    return get_all_registries(db)

@router.get("/{registry_id}", response_model=ContainerRegistry)
def read_registry(registry_id: int, db: Session = Depends(get_db)):
    db_registry = get_registry(db, registry_id)
    if db_registry is None:
        raise HTTPException(status_code=404, detail="Registry not found")
    return db_registry

@router.post("/", response_model=ContainerRegistry)
def create_new_registry(registry: ContainerRegistryCreate, db: Session = Depends(get_db)):
    db_registry = get_registry_by_name(db, registry.name)
    if db_registry:
        raise HTTPException(status_code=400, detail="Registry with this name already exists")
    return create_registry(db, registry)

@router.put("/{registry_id}", response_model=ContainerRegistry)
def update_existing_registry(registry_id: int, registry: ContainerRegistryUpdate, db: Session = Depends(get_db)):
    db_registry = update_registry(db, registry_id, registry)
    if db_registry is None:
        raise HTTPException(status_code=404, detail="Registry not found")
    return db_registry

@router.delete("/{registry_id}")
def delete_existing_registry(registry_id: int, db: Session = Depends(get_db)):
    success = delete_registry(db, registry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Registry not found")
    return {"message": "Registry deleted successfully"}