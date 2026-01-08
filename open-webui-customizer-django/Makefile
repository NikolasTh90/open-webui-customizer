.PHONY: help install dev test lint format clean db-setup db-reset server shell

# Default target
help:
	@echo "Available commands:"
	@echo "  install     Install development dependencies"
	@echo "  dev         Set up development environment"
	@echo "  test        Run tests"
	@echo "  lint        Run code linting"
	@echo "  format      Format code"
	@echo "  clean       Clean up temporary files"
	@echo "  db-setup    Set up database"
	@echo "  db-reset    Reset database"
	@echo "  server      Start development server"
	@echo "  shell       Open Django shell"
	@echo "  migrate     Run database migrations"
	@echo "  makemigrations Create new migrations"
	@echo "  collectstatic Collect static files"
	@echo "  superuser   Create superuser"

# Development setup
install:
	pip install -r requirements/development.txt
	pre-commit install

dev: install db-setup

# Database operations
db-setup:
	python manage.py migrate
	python manage.py collectstatic --noinput

db-reset:
	python manage.py flush --no-input
	python manage.py migrate

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

collectstatic:
	python manage.py collectstatic --noinput

# Development server
server:
	python manage.py runserver

shell:
	python manage.py shell

superuser:
	python manage.py createsuperuser

# Testing
test:
	pytest

test-cov:
	pytest --cov=apps --cov-report=html

test-watch:
	ptw --runner "python -m pytest" -- tests/

# Code quality
lint:
	flake8 .
	mypy .
	black --check .
	isort --check-only .

format:
	black .
	isort .

# Security
security:
	bandit -r . -f json -o bandit-report.json
	safety check --json --output safety-report.json

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf build
	rm -rf dist

# Docker commands
docker-build:
	docker build -t open-webui-customizer-django .

docker-run:
	docker-compose -f docker/docker-compose.yml up -d

docker-stop:
	docker-compose -f docker/docker-compose.yml down

docker-logs:
	docker-compose -f docker/docker-compose.yml logs -f

# Production deployment
deploy-staging:
	export DJANGO_SETTINGS_MODULE=config.settings.staging
	pip install -r requirements/staging.txt
	python manage.py migrate
	python manage.py collectstatic --noinput
	gunicorn config.wsgi:application --bind 0.0.0.0:8000

deploy-production:
	export DJANGO_SETTINGS_MODULE=config.settings.production
	pip install -r requirements/production.txt
	python manage.py migrate
	python manage.py collectstatic --noinput
	gunicorn config.wsgi:application --bind 0.0.0.0:8000

# Database backups
backup:
	@echo "Creating database backup..."
	@mkdir -p backups
	@python manage.py dumpdata --natural-foreign --natural-primary > backups/backup-$(shell date +%Y%m%d-%H%M%S).json

restore:
	@echo "Usage: make restore BACKUP_FILE=path/to/backup.json"
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Error: BACKUP_FILE not specified"; exit 1; fi
	python manage.py loaddata $(BACKUP_FILE)

# Development helpers
watch:
	@echo "Watching for file changes..."
	@find . -name "*.py" | entr -r python manage.py runserver

deps-outdated:
	pip list --outdated

deps-update:
	pip install --upgrade pip
	pip install --upgrade -r requirements/development.txt

# Documentation
docs:
	@echo "Open API documentation at http://localhost:8000/api/docs"
	python manage.py runserver & sleep 2 && xdg-open http://localhost:8000/api/docs

# Performance profiling
profile:
	python manage.py runserver --settings=config.settings.profiling

# Load testing
load-test:
	@echo "Running load tests..."
	@pip install locust
	locust -f tests/load_test.py --host=http://localhost:8000