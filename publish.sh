#!/bin/bash

set -e    # Exit on error
set -x    # Print commands before executing them (helpful for debugging)

# Function to log steps
log_step() {
    echo "----------------------------------------"
    echo "🚀 $1"
    echo "----------------------------------------"
}

# Detect container engine
if command -v podman >/dev/null 2>&1; then
    CONTAINER_ENGINE="podman"
elif command -v docker >/dev/null 2>&1; then
    CONTAINER_ENGINE="docker"
else
    echo "❌ Neither podman nor docker found. Please install one of them."
    exit 1
fi

echo "🐋 Using container engine: ${CONTAINER_ENGINE}"

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo "❌ .env file not found. Please copy .env.example to .env and fill in your values"
    exit 1
fi

# Validate required variables
for var in AWS_ACCOUNT AWS_REGION REPO_NAME; do
    if [ -z "${!var}" ]; then
        echo "❌ Required variable $var is not set"
        exit 1
    fi
done

# Set default values for optional variables
IMAGE_TAG_SUFFIX=${IMAGE_TAG_SUFFIX:-"-custom"}
BASE_IMAGE=${BASE_IMAGE:-"ghcr.io/open-webui/open-webui:main"}

# Construct ECR URL
ECR_URL="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Get version after entering directory
VERSION=$(jq -r .version open-webui/package.json)
echo "Building version: ${VERSION}"

# 1. Check ......................................................
log_step "Check if running"
# TODO look docker images to validate


# 2. Deploy to ECR ..............................................
log_step "Deploying to ECR"
if ! aws ecr get-login-password --region ${AWS_REGION} | ${CONTAINER_ENGINE} login --username AWS --password-stdin ${ECR_URL}; then
    echo "❌ Failed to login to ECR"
    exit 1
fi

if ! ${CONTAINER_ENGINE} tag ${BASE_IMAGE} ${ECR_URL}/${REPO_NAME}:v${VERSION}${IMAGE_TAG_SUFFIX}; then
    echo "❌ Failed to tag image"
    exit 1
fi

if ! ${CONTAINER_ENGINE} push ${ECR_URL}/${REPO_NAME}:v${VERSION}${IMAGE_TAG_SUFFIX}; then
    echo "❌ Failed to push image"
    exit 1
fi

log_step "✅ Deployment completed successfully"
echo "Image: ${ECR_URL}/${REPO_NAME}:v${VERSION}${IMAGE_TAG_SUFFIX}"
