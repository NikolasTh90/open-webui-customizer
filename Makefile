# Makefile for Open WebUI Customizer

# Default values
IMAGE_TAG_SUFFIX ?= -custom
AWS_ACCOUNT_ID ?= 
AWS_REGION ?= 
ECR_REPOSITORY ?= 
BASE_IMAGE ?= ghcr.io/open-webui/open-webui:main

# Export environment variables
export IMAGE_TAG_SUFFIX
export AWS_ACCOUNT_ID
export AWS_REGION
export ECR_REPOSITORY
export BASE_IMAGE

# Default target
all: source build publish clean

# Initialize the application and fetch Open WebUI source
source:
	@echo "Fetching and preparing Open WebUI source..."
	@if [ ! -d "open-webui" ]; then \
		git submodule update --init --recursive; \
	else \
		git submodule update --recursive; \
	fi
	@echo "Source preparation complete."

# Build the frontend and Docker image
build:
	@echo "Building frontend and Docker image..."
	@cd open-webui && npm run build
	@docker build -t open-webui-customized .
	@echo "Build complete."

# Publish the Docker image to AWS ECR
publish:
	@echo "Publishing Docker image to AWS ECR..."
	@aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
	@docker tag open-webui-customized:latest $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPOSITORY):latest$(IMAGE_TAG_SUFFIX)
	@docker push $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPOSITORY):latest$(IMAGE_TAG_SUFFIX)
	@echo "Publish complete."

# Clean up temporary files and reset submodules
clean:
	@echo "Cleaning up..."
	@rm -rf open-webui/build
	@rm -rf open-webui/node_modules
	@docker system prune -f
	@echo "Cleanup complete."

# Install Python dependencies
install:
	@echo "Installing Python dependencies..."
	@pip install -r requirements.txt
	@echo "Python dependencies installed."

# Run database migrations
migrate:
	@echo "Running database migrations..."
	@alembic upgrade head
	@echo "Database migrations complete."

# Run the application
run:
	@echo "Starting the application..."
	@python run.py

# Run the application in development mode
dev:
	@echo "Starting the application in development mode..."
	@uvicorn app.main:app --reload

.PHONY: all source build publish clean install migrate run dev
