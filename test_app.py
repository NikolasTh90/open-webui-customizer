import unittest
import sys
import os
import json

# Add the current directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.models.database import get_db
from app.models.models import BrandingTemplate, BrandingAsset, ContainerRegistry, PipelineRun
from app.schemas.branding import BrandingTemplateCreate, BrandingAssetCreate
from app.schemas.registry import ContainerRegistryCreate

class TestApp(unittest.TestCase):
    def setUp(self):
        # Create a test client
        self.client = TestClient(app)
        
        # Get a database session
        self.db = next(get_db())
        
        # Create test data
        self.create_test_data()
    
    def create_test_data(self):
        # Create a test container registry with a unique name using timestamp
        import time
        timestamp = int(time.time())
        registry_data = ContainerRegistryCreate(
            name=f"Test Registry {timestamp}",
            registry_type="aws_ecr",
            aws_account_id="123456789012",
            aws_region="us-west-2",
            repository_name="test-repo",
            base_image="ghcr.io/open-webui/open-webui:main",
            target_image="test-repo:latest-custom"
        )
        self.registry = ContainerRegistry(**registry_data.model_dump())
        self.db.add(self.registry)
        self.db.commit()
        self.db.refresh(self.registry)
        
        # Create a test branding template with a unique name using timestamp
        template_data = BrandingTemplateCreate(
            name=f"Test Template {timestamp}",
            description="A test template for unit testing",
            brand_name="Test WebUI",
            replacement_rules={
                "OPEN_WEBUI": "Test WebUI",
                "OPEN_WEBUI_VERSION": "1.0.0-test"
            }
        )
        self.template = BrandingTemplate(**template_data.model_dump())
        self.db.add(self.template)
        self.db.commit()
        self.db.refresh(self.template)
    
    def tearDown(self):
        # Clean up test data
        try:
            self.db.delete(self.template)
            self.db.commit()
        except:
            self.db.rollback()
        
        try:
            self.db.delete(self.registry)
            self.db.commit()
        except:
            self.db.rollback()
        
        # Close the database session
        self.db.close()
    
    def test_get_branding_templates(self):
        response = self.client.get("/api/v1/branding/templates")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
    
    def test_create_branding_template(self):
        # First, delete any existing template with the same name to avoid conflicts
        existing_template_response = self.client.get("/api/v1/branding/templates")
        if existing_template_response.status_code == 200:
            templates = existing_template_response.json()
            for template in templates:
                if template["name"] == "New Test Template":
                    self.client.delete(f"/api/v1/branding/templates/{template['id']}")
        
        template_data = {
            "name": "New Test Template",
            "description": "A new test template",
            "brand_name": "Test Brand",
            "replacement_rules": {
                "TEST_KEY": "test_value"
            }
        }
        response = self.client.post("/api/v1/branding/templates", json=template_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], template_data["name"])
        self.assertEqual(data["description"], template_data["description"])
        self.assertEqual(data["brand_name"], template_data["brand_name"])
        self.assertEqual(data["replacement_rules"], template_data["replacement_rules"])
    
    def test_get_container_registries(self):
        response = self.client.get("/api/v1/registries/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
    
    def test_create_container_registry(self):
        # First, delete any existing registry with the same name to avoid conflicts
        existing_registry_response = self.client.get("/api/v1/registries/")
        if existing_registry_response.status_code == 200:
            registries = existing_registry_response.json()
            for registry in registries:
                if registry["name"] == "New Test Registry":
                    self.client.delete(f"/api/v1/registries/{registry['id']}")
        
        registry_data = {
            "name": "New Test Registry",
            "registry_type": "docker_hub",
            "username": "testuser",
            "password": "testpass",
            "aws_account_id": None,
            "aws_region": None,
            "repository_name": None,
            "base_image": "ghcr.io/open-webui/open-webui:main",
            "target_image": "new-test-registry:latest-custom"
        }
        response = self.client.post("/api/v1/registries/", json=registry_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], registry_data["name"])
        self.assertEqual(data["registry_type"], registry_data["registry_type"])

    def test_export_import_template(self):
        # Create a test template first
        template_data = {
            "name": "Export Test Template",
            "description": "Template for testing export/import",
            "brand_name": "Test Brand",
            "replacement_rules": {
                "TEST_KEY": "test_value"
            }
        }
        response = self.client.post("/api/v1/branding/templates", json=template_data)
        self.assertEqual(response.status_code, 200)
        created_template = response.json()
        
        # Export the template
        response = self.client.get(f"/api/v1/branding/templates/{created_template['id']}/export")
        self.assertEqual(response.status_code, 200)
        export_data = response.json()
        
        # Verify export data structure
        self.assertIn("template", export_data)
        self.assertIn("assets", export_data)
        self.assertEqual(export_data["template"]["name"], template_data["name"])
        
        # Import the template (with a new name to avoid conflicts)
        export_data["template"]["name"] = "Imported Test Template"
        import_response = self.client.post(
            "/api/v1/branding/templates/import",
            files={"file": ("template.json", json.dumps(export_data), "application/json")}
        )
        self.assertEqual(import_response.status_code, 200)
        import_data = import_response.json()
        self.assertIn("template_id", import_data)

if __name__ == "__main__":
    unittest.main()