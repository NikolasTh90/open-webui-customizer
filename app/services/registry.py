from sqlalchemy.orm import Session
from app.models.models import ContainerRegistry
from app.schemas.branding import ContainerRegistryCreate, ContainerRegistryUpdate
from typing import List, Optional

def get_registry(db: Session, registry_id: int) -> Optional[ContainerRegistry]:
    return db.query(ContainerRegistry).filter(ContainerRegistry.id == registry_id).first()

def get_registry_by_name(db: Session, name: str) -> Optional[ContainerRegistry]:
    return db.query(ContainerRegistry).filter(ContainerRegistry.name == name).first()

def get_all_registries(db: Session) -> List[ContainerRegistry]:
    return db.query(ContainerRegistry).all()

def create_registry(db: Session, registry: ContainerRegistryCreate) -> ContainerRegistry:
    db_registry = ContainerRegistry(
        name=registry.name,
        registry_type=registry.registry_type,
        base_image=registry.base_image,
        target_image=registry.target_image,
        aws_account_id=registry.aws_account_id,
        aws_region=registry.aws_region,
        repository_name=registry.repository_name,
        username=registry.username,
        password=registry.password
    )
    db.add(db_registry)
    db.commit()
    db.refresh(db_registry)
    return db_registry

def update_registry(db: Session, registry_id: int, registry: ContainerRegistryUpdate) -> Optional[ContainerRegistry]:
    db_registry = get_registry(db, registry_id)
    if db_registry:
        update_data = registry.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_registry, key, value)
        db.commit()
        db.refresh(db_registry)
    return db_registry

def delete_registry(db: Session, registry_id: int) -> bool:
    db_registry = get_registry(db, registry_id)
    if db_registry:
        db.delete(db_registry)
        db.commit()
        return True
    return False