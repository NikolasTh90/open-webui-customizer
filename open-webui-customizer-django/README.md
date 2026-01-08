# Open WebUI Customizer - Django 6 Migration

This is the Django 6 migration of the Open WebUI Customizer project, originally built with FastAPI.

## Project Overview

This project provides a web-based interface for customizing Open WebUI with custom branding, building custom forks, and managing Docker registries and credentials.

## Migration Status

✅ **Phase 1 Complete**: Project Setup and Configuration  
⏳ **Phase 2**: Models Migration  
⏳ **Phase 3**: API Endpoints Migration  
⏳ **Phase 4**: Services Migration  
⏳ **Phase 5**: Templates and HTMX Integration  
⏳ **Phase 6**: Testing Migration  
⏳ **Phase 7**: DevOps and Deployment  

## Technology Stack

- **Framework**: Django 6.0+
- **API**: Django REST Framework 3.15+
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Django Templates with HTMX for interactivity
- **Authentication**: Django Auth + JWT
- **Background Tasks**: Celery with Redis
- **Containerization**: Docker & Docker Compose
- **Code Quality**: Black, isort, flake8, mypy, pre-commit

## Project Structure

```
open-webui-customizer-django/
├── config/                    # Django project configuration
│   ├── settings/             # Tiered settings (dev/staging/production)
│   ├── urls.py              # Root URL configuration
│   ├── asgi.py              # ASGI application
│   └── wsgi.py              # WSGI application
├── apps/                     # Django applications
│   ├── core/                # Shared utilities
│   ├── branding/            # Branding management
│   ├── credentials/         # Credential management
│   ├── pipelines/           # Pipeline execution
│   ├── registries/          # Container registries
│   ├── repositories/        # Git repositories
│   └── dashboard/           # Dashboard and UI
├── static/                   # Static files
├── templates/               # Django templates
├── media/                   # User uploads
├── requirements/            # Split requirements files
├── docker/                  # Docker configuration
└── scripts/                 # Utility scripts
```

## Setup Instructions

### Development Setup

1. **Clone and navigate to the project:**
   ```bash
   cd open-webui-customizer-django
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements/development.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server:**
   ```bash
   python manage.py runserver
   ```

8. **Visit the application:**
   - Web Interface: http://localhost:8000
   - Admin Interface: http://localhost:8000/admin
   - API Documentation: http://localhost:8000/api/docs

### Code Quality Setup

1. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

2. **Run code formatting:**
   ```bash
   black .
   isort .
   ```

3. **Run linting:**
   ```bash
   flake8 .
   mypy .
   ```

### Testing

1. **Run tests:**
   ```bash
   pytest
   ```

2. **Run with coverage:**
   ```bash
   pytest --cov=apps --cov-report=html
   ```

## Environment Configuration

### Development (.env)

```bash
# Basic Django settings
DEBUG=True
SECRET_KEY=your-secret-key-here
DJANGO_SETTINGS_MODULE=config.settings.development

# Database
DATABASE_URL=sqlite:///dev.sqlite3

# Security
ENCRYPTION_KEY=your-32-byte-encryption-key-here
```

### Production

Use `config.settings.production` and configure:
- PostgreSQL database
- Redis cache
- Secure settings (HTTPS, HSTS, etc.)
- S3 storage for media files
- Proper secret keys

## Migration from FastAPI

This Django version maintains API compatibility with the original FastAPI version:

### API Endpoints

| FastAPI Route | Django Route | Description |
|---------------|--------------|-------------|
| `/api/v1/branding/` | `/api/v1/branding/` | Branding management |
| `/api/v1/credentials/` | `/api/v1/credentials/` | Credential management |
| `/api/v1/pipelines/` | `/api/v1/pipelines/` | Pipeline execution |
| `/api/v1/registries/` | `/api/v1/registries/` | Container registries |
| `/api/v1/repositories/` | `/api/v1/repositories/` | Git repositories |

### Key Differences

1. **Web Framework**: FastAPI → Django 6
2. **ORM**: SQLAlchemy → Django ORM
3. **Templates**: Jinja2 → Django Templates
4. **Forms**: Pydantic → Django Forms/DRF Serializers
5. **Migrations**: Alembic → Django Migrations
6. **UI**: React/Vue → Django Templates + HTMX

## HTMX Integration

This project uses HTMX for progressive enhancement:

- **Live Search**: Real-time filtering without page reloads
- **Modal Forms**: Inline editing with validation
- **Real-time Updates**: Server-Sent Events for pipeline status
- **Partial Templates**: Efficient HTML updates

## Deployment

### Docker Development

```bash
docker-compose -f docker/docker-compose.dev.yml up
```

### Docker Production

```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Manual Production

1. **Set environment:**
   ```bash
   export DJANGO_SETTINGS_MODULE=config.settings.production
   ```

2. **Install production dependencies:**
   ```bash
   pip install -r requirements/production.txt
   ```

3. **Collect static files:**
   ```bash
   python manage.py collectstatic --noinput
   ```

4. **Run with Gunicorn:**
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:8000
   ```

## Monitoring and Logging

- **Structured Logging**: JSON format with correlation IDs
- **Performance Monitoring**: Django Debug Toolbar (dev), Prometheus (prod)
- **Error Tracking**: Sentry integration
- **Audit Logging**: Security events tracking

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and code quality checks
5. Submit a pull request

## Original FastAPI Project

The original FastAPI project remains available in the parent directory for reference and parallel operation during migration.

## License

[Same as original project]

## Support

For migration-specific issues, refer to:
1. Migration documentation in `../plans/`
2. Django documentation: https://docs.djangoproject.com/
3. DRF documentation: https://www.django-rest-framework.org/