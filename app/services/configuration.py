from sqlalchemy.orm import Session
from app.models.models import Configuration
from app.schemas.branding import ConfigurationCreate, ConfigurationUpdate
from typing import List, Optional

def get_configuration(db: Session, config_id: int) -> Optional[Configuration]:
    return db.query(Configuration).filter(Configuration.id == config_id).first()

def get_configuration_by_key(db: Session, key: str) -> Optional[Configuration]:
    return db.query(Configuration).filter(Configuration.key == key).first()

def get_all_configurations(db: Session) -> List[Configuration]:
    return db.query(Configuration).all()

def create_configuration(db: Session, config: ConfigurationCreate) -> Configuration:
    db_config = Configuration(
        key=config.key,
        value=config.value
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

def update_configuration(db: Session, config_id: int, config: ConfigurationUpdate) -> Optional[Configuration]:
    db_config = get_configuration(db, config_id)
    if db_config:
        update_data = config.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_config, key, value)
        db.commit()
        db.refresh(db_config)
    return db_config

def update_configuration_by_key(db: Session, key: str, value: str) -> Optional[Configuration]:
    db_config = get_configuration_by_key(db, key)
    if db_config:
        db_config.value = value
        db.commit()
        db.refresh(db_config)
    else:
        # Create new configuration if it doesn't exist
        db_config = Configuration(key=key, value=value)
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
    return db_config

def delete_configuration(db: Session, config_id: int) -> bool:
    db_config = get_configuration(db, config_id)
    if db_config:
        db.delete(db_config)
        db.commit()
        return True
    return False