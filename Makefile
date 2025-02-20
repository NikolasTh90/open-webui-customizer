.PHONY: all source build publish clean check-env

# Default target
all: check-env source build publish

# Check for .env file
check-env:
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found"; \
		echo "💡 Copy .env.example to .env and configure it:"; \
		echo "cp .env.example .env"; \
		exit 1; \
	fi

# Source and prepare environment
source: check-env
	@echo "🚀 Sourcing and preparing environment..."
	./source.sh

# Build application
build: check-env
	@echo "🏗️ Building application..."
	./build.sh

# Publish to ECR
publish: check-env
	@echo "📦 Publishing to ECR..."
	./publish.sh

# Clean environment
clean:
	@echo "🧹 Cleaning environment..."
	./clean.sh

# Help target
help:
	@echo "Available targets:"
	@echo "  all      - Run complete pipeline (source, build, publish)"
	@echo "  source   - Prepare environment and customize"
	@echo "  build    - Build application"
	@echo "  publish  - Publish to ECR"
	@echo "  clean    - Clean environment"
	@echo "  help     - Show this help message"
