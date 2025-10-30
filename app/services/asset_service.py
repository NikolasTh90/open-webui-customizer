import os
import shutil
from sqlalchemy.orm import Session
from app.models import models
from app.schemas import branding

class AssetService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_directory = "app/storage/assets"
        os.makedirs(self.asset_directory, exist_ok=True)
    
    def get_assets(self):
        return self.db.query(models.BrandingAsset).all()
    
    def get_asset(self, asset_id: int):
        return self.db.query(models.BrandingAsset).filter(
            models.BrandingAsset.id == asset_id
        ).first()
    
    def upload_asset(self, file, template_id: int):
        # Save file to storage
        file_path = os.path.join(self.asset_directory, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Determine file type based on extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico"]:
            file_type = "image"
        elif file_extension in [".css"]:
            file_type = "css"
        elif file_extension in [".txt"]:
            file_type = "text"
        else:
            file_type = "other"
        
        # Create database entry
        db_asset = models.BrandingAsset(
            file_name=file.filename,
            file_path=file_path,
            file_type=file_type,
            template_id=template_id
        )
        self.db.add(db_asset)
        self.db.commit()
        self.db.refresh(db_asset)
        return db_asset
    
    def delete_asset(self, asset_id: int):
        db_asset = self.get_asset(asset_id)
        if not db_asset:
            return False
            
        # Delete file from storage
        if os.path.exists(db_asset.file_path):
            os.remove(db_asset.file_path)
            
        # Delete from database
        self.db.delete(db_asset)
        self.db.commit()
        return True
    
    def validate_assets(self, template_id: int):
        # Get validation rules
        validation_rules = self.db.query(models.AssetValidationRule).all()
        
        # Check which required assets are missing
        missing_assets = []
        for rule in validation_rules:
            if rule.is_required:
                # Check if asset exists for this template
                asset_exists = self.db.query(models.BrandingAsset).filter(
                    models.BrandingAsset.template_id == template_id,
                    models.BrandingAsset.file_path.contains(rule.file_path)
                ).first()
                
                if not asset_exists:
                    missing_assets.append(rule)
        
        return {
            "is_valid": len(missing_assets) == 0,
            "missing_assets": missing_assets
        }