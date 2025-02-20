#!/bin/bash

set -e    # Exit on error
set -x    # Print commands before executing them (helpful for debugging)

# Function to log steps
log_step() {
    echo "----------------------------------------"
    echo "🚀 $1"
    echo "----------------------------------------"
}

# Variables
REPO_NAME="*****"
AWS_ACCOUNT="************"
AWS_REGION="eu-west-1"
ECR_URL="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Get version after entering directory
VERSION=$(jq -r .version open-webui/package.json)
echo "Building version: ${VERSION}"

# 1. Check ......................................................
log_step "Check if running"
# TODO look docker images to validate


# 2. Deploy to ECR ..............................................
log_step "Deploying to ECR"
if ! aws ecr get-login-password --region ${AWS_REGION} | podman login --username AWS --password-stdin ${ECR_URL}; then
    echo "❌ Failed to login to ECR"
    exit 1
fi

if ! podman tag ghcr.io/open-webui/open-webui:main ${ECR_URL}/${REPO_NAME}:v${VERSION}-custom; then
    echo "❌ Failed to tag image"
    exit 1
fi

if ! podman push ${ECR_URL}/${REPO_NAME}:v${VERSION}-custom; then
    echo "❌ Failed to push image"
    exit 1
fi

log_step "✅ Deployment completed successfully"
echo "Image: ${ECR_URL}/${REPO_NAME}:v${VERSION}-custom"
