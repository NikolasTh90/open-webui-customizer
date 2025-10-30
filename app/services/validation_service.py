from sqlalchemy.orm import Session
from app.models import models
from app.schemas import branding

class ValidationService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_validation_rules(self):
        """Get all asset validation rules"""
        return self.db.query(models.AssetValidationRule).all()
    
    def get_validation_rule(self, rule_id: int):
        """Get a specific asset validation rule"""
        return self.db.query(models.AssetValidationRule).filter(
            models.AssetValidationRule.id == rule_id
        ).first()
    
    def create_validation_rule(self, rule: branding.AssetValidationRuleCreate):
        """Create a new asset validation rule"""
        db_rule = models.AssetValidationRule(
            file_path=rule.file_path,
            file_type=rule.file_type,
            is_required=rule.is_required,
            description=rule.description
        )
        self.db.add(db_rule)
        self.db.commit()
        self.db.refresh(db_rule)
        return db_rule
    
    def update_validation_rule(self, rule_id: int, rule: branding.AssetValidationRuleCreate):
        """Update an existing asset validation rule"""
        db_rule = self.get_validation_rule(rule_id)
        if not db_rule:
            return None
            
        db_rule.file_path = rule.file_path
        db_rule.file_type = rule.file_type
        db_rule.is_required = rule.is_required
        db_rule.description = rule.description
        
        self.db.commit()
        self.db.refresh(db_rule)
        return db_rule
    
    def delete_validation_rule(self, rule_id: int):
        """Delete an asset validation rule"""
        db_rule = self.get_validation_rule(rule_id)
        if not db_rule:
            return False
            
        self.db.delete(db_rule)
        self.db.commit()
        return True
    
    def initialize_default_rules(self):
        """Initialize default validation rules if none exist"""
        existing_rules = self.db.query(models.AssetValidationRule).count()
        if existing_rules > 0:
            return
            
        # Default validation rules based on the current customization structure
        default_rules = [
            {
                "file_path": "favicon.png",
                "file_type": "image",
                "is_required": True,
                "description": "Main favicon image"
            },
            {
                "file_path": "static/favicon.ico",
                "file_type": "image",
                "is_required": False,
                "description": "ICO format favicon"
            },
            {
                "file_path": "static/favicon.svg",
                "file_type": "image",
                "is_required": False,
                "description": "SVG format favicon"
            },
            {
                "file_path": "static/apple-touch-icon.png",
                "file_type": "image",
                "is_required": False,
                "description": "Apple touch icon"
            },
            {
                "file_path": "themes/",
                "file_type": "css",
                "is_required": False,
                "description": "Custom CSS theme files"
            },
            {
                "file_path": "robots.txt",
                "file_type": "text",
                "is_required": True,
                "description": "Robots.txt file"
            }
        ]
        
        for rule_data in default_rules:
            db_rule = models.AssetValidationRule(**rule_data)
            self.db.add(db_rule)
        
        self.db.commit()