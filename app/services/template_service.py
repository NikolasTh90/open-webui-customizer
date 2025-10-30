from sqlalchemy.orm import Session
from app.models import models
from app.schemas import branding

class TemplateService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_templates(self):
        return self.db.query(models.BrandingTemplate).all()
    
    def get_template(self, template_id: int):
        return self.db.query(models.BrandingTemplate).filter(
            models.BrandingTemplate.id == template_id
        ).first()
    
    def create_template(self, template: branding.BrandingTemplateCreate):
        db_template = models.BrandingTemplate(
            name=template.name,
            description=template.description
        )
        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        
        # Create associated configurations
        for config in template.configurations:
            db_config = models.Configuration(
                key=config.key,
                value=config.value,
                category=config.category,
                template_id=db_template.id
            )
            self.db.add(db_config)
        
        self.db.commit()
        return db_template
    
    def update_template(self, template_id: int, template: branding.BrandingTemplateCreate):
        db_template = self.get_template(template_id)
        if not db_template:
            return None
            
        db_template.name = template.name
        db_template.description = template.description
        db_template.configurations = []  # Clear existing configurations
        
        # Add new configurations
        for config in template.configurations:
            db_config = models.Configuration(
                key=config.key,
                value=config.value,
                category=config.category,
                template_id=template_id
            )
            db_template.configurations.append(db_config)
        
        self.db.commit()
        self.db.refresh(db_template)
        return db_template
    
    def delete_template(self, template_id: int):
        db_template = self.get_template(template_id)
        if not db_template:
            return False
            
        self.db.delete(db_template)
        self.db.commit()
        return True