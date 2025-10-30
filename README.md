# Open WebUI Customizer

A modern web-based UI tool for creating custom-branded OCI (Docker) images of the Open Web UI application. This tool allows you to build and publish your own branded version of Open Web UI while maintaining compatibility with upstream updates.

## Features

- **Web-based UI**: Intuitive interface for managing branding templates and container registries
- **Branding Template Management**: Create and manage templates with replacement rules for text
- **Asset Management**: Upload and manage branding assets (logos, favicons, themes, etc.)
- **Container Registry Support**: Configure multiple registries (AWS ECR, Docker Hub, Quay.io)
- **Pipeline Execution**: Run customizable workflows for cloning, building, and publishing
- **Process Monitoring**: View real-time logs and status of pipeline executions
- **Drag & Drop Uploads**: Easily upload branding assets with drag and drop functionality

## Architecture

The Open WebUI Customizer uses a 4-stage pipeline process:

1. **Source**: Clones/fetches the latest Open Web UI code and prepares the environment
2. **Build**: Builds the Svelte frontend application and creates a Docker container
3. **Publish**: Publishes the customized Docker image to container registries
4. **Clean**: Cleans up the environment and resets submodules

## Prerequisites

- Python 3.8 or higher
- Docker or Podman
- Node.js and npm (for building the frontend)
- Git

For AWS ECR publishing:
- AWS CLI configured with appropriate credentials
- For Docker Hub or Quay.io: Account credentials

## Installation

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

## Usage

### Starting the Application

Run the application with:
```bash
python run.py
```

For development with auto-reload:
```bash
python run.py --reload
```

The application will be available at `http://127.0.0.1:8000`.

### Web UI Navigation

- **Dashboard** (`/`): Overview of the application and recent pipeline runs
- **Branding Templates** (`/branding`): Create and manage branding templates
- **Registries** (`/registries`): Configure container registries
- **Pipeline** (`/pipeline`): Execute customization pipelines

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

## API Endpoints

### Branding Templates
- `GET /api/v1/branding/templates` - List all templates
- `GET /api/v1/branding/templates/{id}` - Get a specific template
- `POST /api/v1/branding/templates` - Create a new template
- `PUT /api/v1/branding/templates/{id}` - Update a template
- `DELETE /api/v1/branding/templates/{id}` - Delete a template

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

## Configuration

The application can be configured through environment variables or the web UI:

### Environment Variables
- `DATABASE_URL`: Database connection string (optional, defaults to SQLite)
- `CUSTOMIZATION_DIR`: Directory for storing branding assets (optional)

## Development

### Running Tests

Execute the test suite:
```bash
python test_app.py
```

### Project Structure

```
open-webui-customizer/
├── app/
│   ├── api/          # REST API endpoints
│   ├── models/       # Database models
│   ├── schemas/     # Pydantic schemas
│   ├── services/    # Business logic
│   ├── templates/   # HTML templates
│   └── static/      # Static assets
├── customization/   # Branding assets storage
├── open-webui/      # Git submodule for Open WebUI source
├── test_app.py      # Test suite
├── run.py           # Application entry point
└── requirements.txt # Python dependencies
```

### Extending Functionality

To add new features:
1. Create new schemas in `app/schemas/`
2. Add database models in `app/models/models.py`
3. Implement business logic in `app/services/`
4. Create API endpoints in `app/api/`
5. Add UI templates in `app/templates/`
6. Register new routes in `app/main.py`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.
