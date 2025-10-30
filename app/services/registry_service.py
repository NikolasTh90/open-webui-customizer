import json
from sqlalchemy.orm import Session
from app.models import models
from app.schemas import branding

class RegistryService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_registries(self):
        return self.db.query(models.Registry).all()
    
    def get_registry(self, registry_id: int):
        return self.db.query(models.Registry).filter(
            models.Registry.id == registry_id
        ).first()
    
    def get_active_registry(self):
        return self.db.query(models.Registry).filter(
            models.Registry.is_active == True
        ).first()
    
    def create_registry(self, registry: branding.RegistryCreate):
        db_registry = models.Registry(
            name=registry.name,
            type=registry.type,
            config_json=registry.config_json,
            is_active=registry.is_active
        )
        self.db.add(db_registry)
        self.db.commit()
        self.db.refresh(db_registry)
        return db_registry
    
    def update_registry(self, registry_id: int, registry: branding.RegistryCreate):
        db_registry = self.get_registry(registry_id)
        if not db_registry:
            return None
            
        db_registry.name = registry.name
        db_registry.type = registry.type
        db_registry.config_json = registry.config_json
        db_registry.is_active = registry.is_active
        
        self.db.commit()
        self.db.refresh(db_registry)
        return db_registry
    
    def delete_registry(self, registry_id: int):
        db_registry = self.get_registry(registry_id)
        if not db_registry:
            return False
            
        self.db.delete(db_registry)
        self.db.commit()
        return True
    
    def get_registry_config(self, registry_id: int):
        """Get registry configuration as a dictionary"""
        db_registry = self.get_registry(registry_id)
        if not db_registry:
            return None
            
        try:
            return json.loads(db_registry.config_json)
        except json.JSONDecodeError:
            return {}