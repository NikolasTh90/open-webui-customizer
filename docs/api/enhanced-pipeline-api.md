# Enhanced Pipeline API Documentation

## Overview

The Enhanced Pipeline API provides functionality for building custom Open WebUI packages from both the official repository and custom Git forks. This API supports flexible build steps, multiple output types (ZIP files and Docker images), and comprehensive credential management.

## Base URL

```
/api/pipelines
```

## Authentication

All API endpoints require appropriate authentication. Please ensure your requests include valid authentication headers.

## Endpoints

### Pipeline Runs

#### GET /api/pipelines/runs

Get all pipeline runs with optional filtering.

**Query Parameters:**
- `status` (string, optional): Filter by pipeline status (`pending`, `running`, `completed`, `failed`)
- `limit` (integer, optional): Maximum number of runs to return (default: no limit)
- `offset` (integer, optional): Offset for pagination (default: 0)

**Response:**
```json
{
  "success": true,
  "runs": [
    {
      "id": 1,
      "status": "completed",
      "steps_to_execute": ["clone_repo", "create_zip"],
      "git_repository_id": 1,
      "output_type": "zip",
      "registry_id": null,
      "started_at": "2024-01-08T10:00:00Z",
      "completed_at": "2024-01-08T10:05:00Z",
      "logs": "Pipeline run created. Waiting for execution...\n[2024-01-08T10:00:00Z] Starting pipeline execution...\n...",
      "repository_info": {
        "id": 1,
        "name": "My Custom Fork",
        "url": "git@github.com:user/open-webui.git",
        "type": "ssh",
        "is_verified": true
      },
      "build_outputs": [...]
    }
  ],
  "count": 1
}
```

#### POST /api/pipelines/runs

Create a new pipeline run.

**Request Body:**
```json
{
  "steps_to_execute": ["clone_repo", "create_zip"],
  "git_repository_id": 1,
  "output_type": "zip",
  "registry_id": null,
  "custom_parameters": {}
}
```

**Field Descriptions:**
- `steps_to_execute` (array): List of build steps to execute. Available steps:
  - `clone_repo` (required): Clone Git repository
  - `apply_branding`: Apply branding template
  - `apply_config`: Apply configuration settings
  - `create_zip`: Create ZIP archive
  - `build_image`: Build Docker image
  - `push_registry`: Push to container registry
- `git_repository_id` (integer, optional): Custom Git repository ID. If omitted, uses official repository.
- `output_type` (string, required): Output type - `zip`, `docker_image`, or `both`
- `registry_id` (integer, optional): Container registry ID (required if `push_registry` step is included)
- `custom_parameters` (object, optional): Additional parameters

**Response:**
```json
{
  "success": true,
  "pipeline_run": {
    "id": 2,
    "status": "pending",
    "steps_to_execute": ["clone_repo", "create_zip"],
    "git_repository_id": 1,
    "output_type": "zip",
    "registry_id": null,
    "started_at": "2024-01-08T10:10:00Z",
    "completed_at": null,
    "logs": "Pipeline run created. Waiting for execution.\n"
  }
}
```

#### GET /api/pipelines/runs/{run_id}

Get a specific pipeline run.

**Path Parameters:**
- `run_id` (integer): Pipeline run ID

**Response:**
```json
{
  "success": true,
  "pipeline_run": {
    "id": 1,
    "status": "completed",
    "steps_to_execute": ["clone_repo", "create_zip"],
    "git_repository_id": 1,
    "output_type": "zip",
    "registry_id": null,
    "started_at": "2024-01-08T10:00:00Z",
    "completed_at": "2024-01-08T10:05:00Z",
    "logs": "Pipeline execution logs...",
    "repository_info": {...},
    "build_outputs": [...]
  }
}
```

#### POST /api/pipelines/runs/{run_id}/execute

Execute a pipeline run.

**Path Parameters:**
- `run_id` (integer): Pipeline run ID

**Response:**
```json
{
  "success": true,
  "execution_result": {
    "success": true,
    "message": "Pipeline completed successfully with 1 output(s)"
  }
}
```

#### GET /api/pipelines/runs/{run_id}/logs

Get the logs for a pipeline run.

**Path Parameters:**
- `run_id` (integer): Pipeline run ID

**Response:**
Returns plain text logs:
```
[2024-01-08T10:00:00Z] Pipeline run created. Waiting for execution.
[2024-01-08T10:01:00Z] Starting pipeline execution...
[2024-01-08T10:01:01Z] Executing step: Clone Git Repository
[2024-01-08T10:01:01Z] ✓ Step completed: Clone Git Repository
[2024-01-08T10:01:30Z] Executing step: Create ZIP Archive
[2024-01-08T10:01:35Z] ✓ Step completed: Create ZIP Archive
[2024-01-08T10:01:35Z] Pipeline completed successfully. Generated 1 output(s).
```

### Build Outputs

#### GET /api/pipelines/runs/{run_id}/outputs

Get all build outputs for a pipeline run.

**Path Parameters:**
- `run_id` (integer): Pipeline run ID

**Response:**
```json
{
  "success": true,
  "build_outputs": [
    {
      "id": 1,
      "output_type": "zip",
      "file_path": "/tmp/builds/open_webui_custom_20240108_101500.zip",
      "file_size_bytes": 52428800,
      "checksum_sha256": "a1b2c3d4e5f6...",
      "download_count": 0,
      "expires_at": "2024-01-15T10:01:35Z",
      "created_at": "2024-01-08T10:01:35Z",
      "download_url": "/api/pipelines/outputs/1/download"
    },
    {
      "id": 2,
      "output_type": "docker_image",
      "image_url": "open-webui-custom:20240108_101505",
      "download_count": 0,
      "expires_at": "2024-01-09T10:01:35Z",
      "created_at": "2024-01-08T10:02:00Z"
    }
  ],
  "count": 2
}
```

#### GET /api/pipelines/outputs/{output_id}/download

Download a build output file.

**Path Parameters:**
- `output_id` (integer): Build output ID

**Response:**
Returns the file as a downloadable attachment.

### Build Steps

#### GET /api/pipelines/steps

Get information about all available build steps.

**Response:**
```json
{
  "success": true,
  "build_steps": [
    {
      "key": "clone_repo",
      "name": "Clone Git Repository",
      "description": "Clone the Git repository (official or custom fork)",
      "order": 1,
      "required": true
    },
    {
      "key": "apply_branding",
      "name": "Apply Branding Template",
      "description": "Apply selected branding template",
      "order": 2,
      "required": false
    },
    {
      "key": "create_zip",
      "name": "Create ZIP Archive",
      "description": "Package customizations into a ZIP file",
      "order": 4,
      "required": false
    }
  ],
  "count": 6
}
```

### Statistics and Maintenance

#### GET /api/pipelines/statistics

Get pipeline execution statistics.

**Query Parameters:**
- `days` (integer, optional): Number of days to look back (default: 30)

**Response:**
```json
{
  "success": true,
  "statistics": {
    "period_days": 30,
    "total_runs": 25,
    "completed_runs": 20,
    "failed_runs": 3,
    "running_runs": 1,
    "pending_runs": 1,
    "success_rate": 80.0,
    "step_usage": {
      "clone_repo": 25,
      "create_zip": 20,
      "build_image": 15,
      "push_registry": 10
    },
    "output_types": {
      "zip": 15,
      "docker_image": 8,
      "both": 2
    },
    "total_build_outputs": 35
  }
}
```

#### POST /api/pipelines/cleanup

Clean up expired build outputs.

**Response:**
```json
{
  "success": true,
  "cleanup_result": {
    "total_cleaned": 5,
    "files_cleaned": 3,
    "images_cleaned": 2
  }
}
```

### Repository Usage

#### GET /api/pipelines/repositories/{repository_id}/usage

Get usage statistics for a specific Git repository.

**Path Parameters:**
- `repository_id` (integer): Repository ID

**Response:**
```json
{
  "success": true,
  "repository_usage": {
    "repository_id": 1,
    "repository_name": "My Custom Fork",
    "repository_url": "git@github.com:user/open-webui.git",
    "is_verified": true,
    "total_pipeline_runs": 10,
    "completed_runs": 8,
    "failed_runs": 1,
    "success_rate": 80.0,
    "total_build_outputs": 12,
    "last_used_at": "2024-01-08T09:30:00Z",
    "created_at": "2024-01-01T10:00:00Z"
  }
}
```

## Error Responses

All endpoints may return error responses with the following structure:

```json
{
  "error": "Error Type",
  "message": "Detailed error message"
}
```

### Common Error Codes

- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource already exists
- `500 Internal Server Error`: Server error

### Error Types

- `Validation error`: Input validation failed
- `Resource not found`: Requested resource does not exist
- `Database error`: Database operation failed
- `Execution error`: Pipeline execution failed
- `Download error`: File download failed

## Usage Examples

### Example 1: Create and Execute a Simple Pipeline

```bash
# Create a pipeline run for ZIP output
curl -X POST "https://your-domain.com/api/pipelines/runs" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "steps_to_execute": ["clone_repo", "create_zip"],
    "output_type": "zip"
  }'

# Execute the pipeline (assuming run_id = 1)
curl -X POST "https://your-domain.com/api/pipelines/runs/1/execute" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Example 2: Build Custom Fork with Docker Image

```bash
# Create pipeline for custom repository
curl -X POST "https://your-domain.com/api/pipelines/runs" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "steps_to_execute": ["clone_repo", "build_image", "push_registry"],
    "git_repository_id": 2,
    "output_type": "docker_image",
    "registry_id": 1
  }'
```

### Example 3: Monitor Pipeline Execution

```bash
# Get pipeline logs
curl -X GET "https://your-domain.com/api/pipelines/runs/1/logs" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get build outputs
curl -X GET "https://your-domain.com/api/pipelines/runs/1/outputs" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Download ZIP output
curl -X GET "https://your-domain.com/api/pipelines/outputs/1/download" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o "open-webui-custom.zip"
```

## Build Step Dependencies

Some build steps have dependencies on others:

| Step | Dependencies |
|------|-------------|
| `create_zip` | `clone_repo` |
| `build_image` | `clone_repo` |
| `push_registry` | `clone_repo`, `build_image` |
| `apply_branding` | `clone_repo` |
| `apply_config` | `clone_repo` |

The API will validate step dependencies and return an error if invalid combinations are provided.

## Output Retention

Build outputs have automatic expiration:

- ZIP files: 7 days
- Docker images: 1 day (local images)
- Registry images: Persistent (until manually removed)

Use the cleanup endpoint to remove expired outputs.

## Rate Limiting

API endpoints may have rate limiting applied. Check response headers for rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1641628800
```

## WebSocket Support

For real-time pipeline execution monitoring, WebSocket connections are available:

```
ws://your-domain.com/api/pipelines/runs/{run_id}/ws
```

WebSocket messages contain pipeline status updates and log lines.

## SDK Examples

### Python

```python
import requests

# Create pipeline run
response = requests.post(
    "https://your-domain.com/api/pipelines/runs",
    headers={
        "Authorization": "Bearer YOUR_TOKEN",
        "Content-Type": "application/json"
    },
    json={
        "steps_to_execute": ["clone_repo", "create_zip"],
        "output_type": "zip"
    }
)

run_data = response.json()
run_id = run_data["pipeline_run"]["id"]

# Execute pipeline
requests.post(
    f"https://your-domain.com/api/pipelines/runs/{run_id}/execute",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

# Monitor execution
while True:
    response = requests.get(
        f"https://your-domain.com/api/pipelines/runs/{run_id}",
        headers={"Authorization": "Bearer YOUR_TOKEN"}
    )
    
    run = response.json()["pipeline_run"]
    print(f"Status: {run['status']}")
    
    if run["status"] in ["completed", "failed"]:
        break
    
    time.sleep(5)
```

### JavaScript

```javascript
// Create pipeline run
const createRun = async () => {
  const response = await fetch('/api/pipelines/runs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      steps_to_execute: ['clone_repo', 'create_zip'],
      output_type: 'zip'
    })
  });
  
  const data = await response.json();
  return data.pipeline_run.id;
};

// Execute run
const executeRun = async (runId) => {
  await fetch(`/api/pipelines/runs/${runId}/execute`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
};

// Monitor progress
const monitorRun = async (runId) => {
  const logs = await fetch(`/api/pipelines/runs/${runId}/logs`);
  return await logs.text();
};
```

## Troubleshooting

### Common Issues

1. **Pipeline creation fails**
   - Check that all required fields are provided
   - Verify step dependencies are satisfied
   - Ensure output type is valid

2. **Execution fails during clone**
   - Verify Git repository is accessible
   - Check credentials are properly configured
   - Ensure repository is verified

3. **Download fails**
   - Check if output has expired
   - Verify output type supports downloading
   - Check permissions on output file

### Debug Mode

Enable debug logging by setting the `DEBUG` environment variable to `true`:

```bash
export DEBUG=true
```

This will provide detailed logs for troubleshooting pipeline issues.

## Changelog

### v1.0.0 (2024-01-08)
- Initial release of Enhanced Pipeline API
- Support for custom Git repository cloning
- Flexible build step configuration
- ZIP and Docker image generation
- Container registry integration
- Comprehensive credential management