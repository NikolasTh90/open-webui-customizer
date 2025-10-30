# Open WebUI Customizer - Comprehensive Documentation

## Project Overview

The Open WebUI Customizer is a modern web-based UI tool designed to create custom-branded OCI (Docker) images of the Open Web UI application. This application allows users to build and publish their own branded version of Open Web UI while maintaining compatibility with upstream updates.

Rather than modifying the original Open Web UI codebase directly, this tool applies customizations as an overlay during the build process, ensuring a clean separation between the original application and custom branding assets.

## Features Implemented

### 1. Web-based User Interface
- Intuitive dashboard for monitoring pipeline executions
- Responsive design using Tailwind CSS
- Dynamic UI updates with HTMX
- Modal dialogs for creating and editing entities

### 2. Branding Template Management
- Create, read, update, and delete branding templates
- Advanced text replacement templating system
- Template export/import functionality as JSON files
- Unique template naming with validation

### 3. Asset Management
- Drag and drop file upload functionality
- Support for various branding asset types:
  - Logos (PNG, JPEG, SVG)
  - Favicons (ICO, PNG)
  - Theme files (CSS)
  - Web manifest files
  - Robots.txt
- File validation to ensure required assets are present
- Asset preview capabilities

### 4. Container Registry Support
- Configurable multiple container registries:
  - AWS ECR
  - Docker Hub
  - Quay.io
- Registry-specific configuration parameters
- Base and target image management

### 5. Pipeline Execution
- Customizable workflow execution with selectable steps:
  - Source: Clone/fetch the latest Open Web UI code
  - Build: Build the Svelte frontend and Docker image
  - Publish: Push the image to the selected registry
  - Clean: Clean up working directories
- Real-time pipeline status monitoring
- Detailed execution logs
- Background task processing

### 6. Configuration Management
- Key-value configuration system
- General application settings management
- Dynamic configuration loading

## Architecture

The application uses a layered architecture with clear separation of concerns:

```
open-webui-customizer/
├── app/
│   ├── api/          # REST API endpoints
│   ├── models/       # Database models
│   ├── schemas/     # Pydantic schemas for data validation
│   ├── services/    # Business logic
│   ├── templates/   # HTML templates with Jinja2
│   └── static/      # Static assets (CSS, JS)
├── customization/   # Branding assets storage
├── open-webui/      # Git submodule for Open WebUI source
├── alembic/         # Database migrations
├── test_app.py      # Test suite
├── run.py           # Application entry point
└── requirements.txt # Python dependencies
```

### Technology Stack
- **FastAPI**: High-performance web framework for building APIs
- **SQLAlchemy**: ORM for database interactions
- **SQLite**: Default database engine
- **HTMX**: Dynamic UI updates without writing JavaScript
- **Tailwind CSS**: Utility-first CSS framework for styling
- **Jinja2**: Template engine for HTML rendering
- **Alembic**: Database migration tool

## Database Schema

The application uses the following database tables:

### Branding Templates
- `id` (Integer): Primary key
- `name` (String): Unique template name
- `description` (Text): Template description
- `brand_name` (String): Brand name to replace "Open WebUI"
- `replacement_rules` (JSON): Key-value pairs for text replacements
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

### Branding Assets
- `id` (Integer): Primary key
- `template_id` (Integer): Foreign key to branding_templates
- `file_name` (String): Original file name
- `file_type` (String): Asset type (logo, favicon, theme, etc.)
- `file_path` (String): Path to the stored file
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

### Container Registries
- `id` (Integer): Primary key
- `name` (String): Unique registry name
- `registry_type` (String): Registry type (aws_ecr, docker_hub, quay_io)
- `base_image` (String): Source Open WebUI image
- `target_image` (String): Custom image name and tag
- `aws_account_id` (String): AWS account ID (nullable)
- `aws_region` (String): AWS region (nullable)
- `repository_name` (String): Repository name (nullable)
- `username` (String): Registry username (nullable)
- `password` (String): Registry password (nullable)
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

### Pipeline Runs
- `id` (Integer): Primary key
- `status` (String): Execution status (pending, running, completed, failed)
- `steps_to_execute` (JSON): Selected pipeline steps
- `started_at` (DateTime): Execution start time
- `completed_at` (DateTime): Execution completion time
- `logs` (Text): Execution logs

### Configurations
- `id` (Integer): Primary key
- `key` (String): Unique configuration key
- `value` (Text): Configuration value
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

## API Endpoints

### Branding Templates
- `GET /api/v1/branding/templates` - List all templates
- `GET /api/v1/branding/templates/{id}` - Get a specific template
- `POST /api/v1/branding/templates` - Create a new template
- `PUT /api/v1/branding/templates/{id}` - Update a template
- `DELETE /api/v1/branding/templates/{id}` - Delete a template
- `GET /api/v1/branding/templates/{template_id}/export` - Export template as JSON
- `POST /api/v1/branding/templates/import` - Import template from JSON

### Branding Assets
- `GET /api/v1/branding/templates/{template_id}/assets` - List assets for a template
- `POST /api/v1/branding/upload` - Upload a new asset
- `DELETE /api/v1/branding/assets/{id}` - Delete an asset

### Container Registries
- `GET /api/v1/registries/` - List all registries
- `GET /api/v1/registries/{id}` - Get a specific registry
- `POST /api/v1/registries/` - Create a new registry
- `PUT /api/v1/registries/{id}` - Update a registry
- `DELETE /api/v1/registries/{id}` - Delete a registry

### Pipeline Runs
- `GET /api/v1/pipeline/runs` - List all pipeline runs
- `GET /api/v1/pipeline/runs/{id}` - Get a specific pipeline run
- `POST /api/v1/pipeline/run` - Start a new pipeline run
- `GET /api/v1/pipeline/runs/{id}/status` - Get pipeline run status
- `GET /api/v1/pipeline/runs/{id}/logs` - Get pipeline run logs

### Configuration
- `GET /api/v1/configuration/` - List all configuration items
- `GET /api/v1/configuration/{id}` - Get a specific configuration
- `POST /api/v1/configuration/` - Create a configuration item
- `PUT /api/v1/configuration/{id}` - Update a configuration item
- `PUT /api/v1/configuration/key/{key}` - Update configuration by key
- `DELETE /api/v1/configuration/{id}` - Delete a configuration item

## UI Routes

### Main Pages
- `/` - Dashboard with pipeline execution overview
- `/branding` - Branding templates list and management
- `/registries` - Container registries list and management
- `/pipeline` - Pipeline execution configuration
- `/configuration` - Application configuration management

### Template Management
- `/branding/create` - Form for creating new branding template
- `/branding/{template_id}/edit` - Form for editing branding template
- `/branding/{template_id}/assets` - Asset management for a template

### Registry Management
- `/registries/create` - Form for creating new container registry
- `/registries/{registry_id}/edit` - Form for editing container registry

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Docker or Podman
- Node.js and npm (for building the frontend)
- Git

For AWS ECR publishing:
- AWS CLI configured with appropriate credentials

For Docker Hub or Quay.io:
- Account credentials

### Installation Steps

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd open-webui-customizer
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize the database:
   The application will automatically create a SQLite database file `database.db` in the app directory on first run.

### Running the Application

Run the application with:
```bash
python run.py
```

For development with auto-reload:
```bash
python run.py --reload
```

The application will be available at `http://127.0.0.1:8000`.

## Usage Guide

### Creating a Branding Template

1. Navigate to the Branding Templates page
2. Click "Create New Template"
3. Fill in the template details:
   - Name: A unique identifier for your template
   - Description: Brief description of the template
   - Brand Name: The name to replace "Open WebUI" with
   - Replacement Rules: Key-value pairs for text replacement
4. Save the template

### Uploading Branding Assets

1. Once a template is created, go to its asset management page
2. Use the drag and drop area or file browser to upload assets
3. Supported asset types:
   - Logos (PNG, JPEG, SVG)
   - Favicons (ICO, PNG)
   - Theme files (CSS)
   - Web manifest files
   - Robots.txt

### Configuring Container Registries

1. Navigate to the Registries page
2. Click "Add Registry"
3. Configure the registry:
   - Name: A unique identifier
   - Type: AWS ECR, Docker Hub, or Quay.io
   - Base Image: The source Open WebUI image
   - Target Image: Your custom image name and tag
   - Registry-specific settings (account ID, region, credentials, etc.)

### Running the Pipeline

1. Navigate to the Pipeline page
2. Select a branding template and registry
3. Choose which steps to execute:
   - Source: Clone/fetch the latest Open WebUI code
   - Build: Build the Svelte frontend and Docker image
   - Publish: Push the image to the selected registry
   - Clean: Clean up working directories
4. Click "Run Pipeline"
5. Monitor progress in the logs section

### Template Export/Import

1. To export a template, click the "Export" button on any template card
2. To import a template, click the "Import Template" button on the branding page
3. Select a JSON file containing exported template data

## Testing

### Running Tests

Execute the test suite:
```bash
python test_app.py
```

### Test Coverage

The current test suite includes tests for:
- Creating and retrieving branding templates
- Creating and retrieving container registries
- Template export/import functionality

## Next Steps

### 1. Enhanced UI Components
- Implement inline editing for configurations in the UI
- Add asset preview functionality in the asset management page
- Improve the dashboard with charts and statistics

### 2. Advanced Pipeline Features
- Add support for custom docker-compose files selection
- Implement pipeline scheduling for automated builds
- Add pipeline history and comparison features

### 3. Configuration Management UI
- Create dedicated pages for viewing and editing configuration items
- Add configuration categories and grouping
- Implement configuration validation

### 4. User Management
- Add authentication and authorization
- Implement user roles and permissions
- Add audit logging for all actions

### 5. Database Migration System
- Implement Alembic migrations for database schema changes
- Add migration history tracking

### 6. Documentation Improvements
- Add detailed API documentation with Swagger UI
- Create user guides for each feature
- Add developer documentation for extending functionality

### 7. Additional Features
- Add support for custom environment variables
- Implement template versioning
- Add pipeline notifications (email, Slack, etc.)