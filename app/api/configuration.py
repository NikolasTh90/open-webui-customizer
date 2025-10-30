from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.branding import Configuration, ConfigurationCreate, ConfigurationUpdate
from app.services.configuration import (
    get_configuration, get_configuration_by_key, get_all_configurations,
    create_configuration, update_configuration, delete_configuration,
    update_configuration_by_key
)
from typing import List

router = APIRouter(prefix="/api/v1/configuration", tags=["configuration"])

@router.get("/", response_model=List[Configuration])
def read_all_configurations(db: Session = Depends(get_db)):
    return get_all_configurations(db)

@router.get("/{config_id}", response_model=Configuration)
def read_configuration(config_id: int, db: Session = Depends(get_db)):
    db_config = get_configuration(db, config_id)
    if db_config is None:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return db_config

@router.post("/", response_model=Configuration)
def create_new_configuration(config: ConfigurationCreate, db: Session = Depends(get_db)):
    db_config = get_configuration_by_key(db, config.key)
    if db_config:
        raise HTTPException(status_code=400, detail="Configuration with this key already exists")
    return create_configuration(db, config)

@router.put("/{config_id}", response_model=Configuration)
def update_existing_configuration(config_id: int, config: ConfigurationUpdate, db: Session = Depends(get_db)):
    db_config = update_configuration(db, config_id, config)
    if db_config is None:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return db_config

@router.put("/key/{key}", response_model=Configuration)
def update_configuration_by_key_endpoint(key: str, value: str, db: Session = Depends(get_db)):
    db_config = update_configuration_by_key(db, key, value)
    if db_config is None:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return db_config

@router.delete("/{config_id}")
def delete_existing_configuration(config_id: int, db: Session = Depends(get_db)):
    success = delete_configuration(db, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration deleted successfully"}