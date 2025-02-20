# Open Web UI - Pipeline customizer

A repository to generate custom OCI images from Open Web UI with customized branding. This tool allows you to build and publish your own branded version of Open Web UI while maintaining compatibility with upstream updates.

## Prerequisites

- Docker or Podman
- Node.js
- AWS CLI configured with ECR access
- jq

## Setup

1. Clone the repository with submodules:
```bash
git clone --recursive [repository-url]
```

2. Configure your environment:
```bash
cp .env.example .env
chmod 600 .env    # Secure your credentials
```

3. Edit `.env` with your AWS and repository settings

## Usage

### Building
To build your custom image:
```bash
./build.sh
```

### Publishing
To publish your image to AWS ECR:
```bash
./publish.sh
```

## Configuration

The following environment variables can be configured in your `.env` file:

- `AWS_ACCOUNT`: Your AWS account ID
- `AWS_REGION`: AWS region for ECR
- `REPO_NAME`: Name of your ECR repository
- `IMAGE_TAG_SUFFIX`: Custom suffix for image tags (default: "-custom")
- `BASE_IMAGE`: Base image to use (default: "ghcr.io/open-webui/open-webui:main")

## License

This project is licensed under the same terms as Open Web UI.

