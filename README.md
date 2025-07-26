# Open Web UI - Pipeline Customizer

A repository to generate custom OCI images from Open Web UI with customized branding. This tool allows you to build and publish your own branded version of Open Web UI while maintaining compatibility with upstream updates.

## Prerequisites

- Docker or Podman
- Node.js
- AWS CLI configured with ECR access
- jq
- make

## Setup

1. Clone the repository with submodules:
```bash
git clone --recursive [repository-url]
cd open-webui-pipeline-customizer
```

2. Configure your environment:
```bash
cp .env.example .env
chmod 600 .env    # Secure your credentials
```

3. Edit `.env` with your AWS and repository settings

## Usage

### Complete pipeline (recommended)
To run the entire pipeline automatically (source, build, publish, and clean):
```bash
make
# or explicitly
make all
```

### Individual steps

#### 1. Prepare environment and customize
```bash
make source
```

#### 2. Build custom image
```bash
make build
```

#### 3. Publish to AWS ECR
```bash
make publish
```

#### 4. Clean environment
```bash
make clean
```

### Show help
```bash
make help
```

## Alternative scripts

You can also use the individual scripts directly:

```bash
# Prepare environment
./source.sh

# Build
./build.sh

# Publish
./publish.sh

# Clean
./clean.sh
```

## Configuration

The following environment variables can be configured in your `.env` file:

- `AWS_ACCOUNT`: Your AWS account ID
- `AWS_REGION`: AWS region for ECR
- `REPO_NAME`: Name of your ECR repository
- `IMAGE_TAG_SUFFIX`: Custom suffix for image tags (default: "-custom")
- `BASE_IMAGE`: Base image to use (default: "ghcr.io/open-webui/open-webui:main")

## Project structure

```
.
├── Makefile              # Pipeline automation
├── .env.example          # Example environment variables
├── source.sh            # Environment preparation script
├── build.sh             # Build script
├── publish.sh           # ECR publishing script
├── clean.sh             # Cleanup script
└── README.md            # This file
```

## License

This project is licensed under the MIT License. 
Related software components have their own licenses as described in [NOTICE.md](./NOTICE.md) or their original sources.

**Important note**: Reference images included have copyright from their respective brands and cannot be used without express permission. This repository is solely a customization tool; you must provide your own branding assets.
