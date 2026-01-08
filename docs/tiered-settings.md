# Tiered Settings Architecture

The Open WebUI Customizer uses a comprehensive tiered settings architecture that provides different configurations for development, staging, and production environments. This system ensures security, performance, and ease of development across all environments.

## Overview

The tiered settings system is built using Pydantic's BaseSettings class with inheritance. Each environment (development, staging, production) inherits from base settings and overrides specific values to meet the requirements of that environment.

### Key Benefits

- **Environment-specific configurations**: Automatically load appropriate settings based on `ENVIRONMENT` variable
- **Security by default**: Production environments have strict security settings
- **Development ease**: Development environments have relaxed restrictions for easier development
-Type safety**: All settings are validated using Pydantic models
- **Environment variable support**: Override any setting using environment variables with nested delimiter (`__`)

## Architecture Diagram

```
BaseSettings (common defaults)
├── DevSettings (default, relaxed restrictions)
├── StagingSettings (intermediate restrictions)
└── ProductionSettings (strict security, performance optimized)
```

## Environment Configurations

### Development Environment (`ENVIRONMENT=development`)

This is the default environment when no `ENVIRONMENT` variable is set. It provides the most relaxed settings for easier development.

#### Key Features:
- **Debug mode**: Enabled for full error details
- **Database**: SQLite with auto table creation and query logging
- **Security**: No encryption key required, CORS allows all origins, rate limiting disabled
- **Git**: Allow any Git host, longer timeouts, larger repository size limits
- **Logging**: DEBUG level with text format for console readability
- **Pipelines**: Relaxed limits and longer timeouts for testing

#### Use Cases:
- Local development
- Feature testing
- Debugging issues
- Quick prototyping

### Staging Environment (`ENVIRONMENT=staging`)

Intermediate environment that mimics production but with some relaxed settings for testing.

#### Key Features:
- **Debug mode**: Disabled
- **Database**: Production-ready database settings with auto table creation
- **Security**: Default encryption key, specific CORS origins, rate limiting enabled
- **Git**: Restricted to known hosts, standard timeouts
- **Logging**: INFO level with JSON format
- **Pipelines**: Production-like limits with some flexibility

#### Use Cases:
- Pre-production testing
- User acceptance testing (UAT)
- Performance testing
- Integration testing

### Production Environment (`ENVIRONMENT=production`)

Strict, secure configuration optimized for production deployment.

#### Key Features:
- **Debug mode**: Disabled
- **Database**: Requires Alembic migrations, no query logging
- **Security**: Requires encryption key, restricted CORS, rate limiting enabled
- **Git**: Strict host validation, standard timeouts
- **Logging**: WARNING level with JSON format
- **Pipelines**: Optimized for performance and resource usage

#### Use Cases:
- Production deployment
- Customer-facing applications
- High-security environments
- Performance-critical deployments

## Settings Hierarchy

### Base Settings

Each configuration area has a base class that provides common defaults:

```python
class Base[Area]Settings(BaseSettings):
    # Common defaults for all environments
```

### Environment-Specific Overrides

Each environment has its own settings class that inherits from the base and overrides specific values:

```python
class Dev[Area]Settings(Base[Area]Settings):
    # Development-specific overrides
```

## Configuration Areas

### 1. Database Settings (`database.*`)

Controls database connection and behavior.

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| `database_url` | SQLite | PostgreSQL | PostgreSQL |
| `echo` | True | False | False |
| `auto_create_tables` | True | True | False |
| `pool_size` | 5 | 10 | 20 |
| `pool_timeout` | 30 | 30 | 60 |

### 2. Security Settings (`security.*`)

Controls authentication, encryption, and access controls.

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| `require_encryption_key` | False | False | True |
| `cors_origins` | `["*"]` | Specific domains | Restricted |
| `rate_limit_enabled` | False | True | True |
| `detailed_errors` | True | True | False |
| `secret_key` | Default | Required | Required |

### 3. Git Settings (`git.*`)

Controls Git repository operations.

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| `allow_any_git_host` | True | False | False |
| `allowed_git_hosts` | All | Limited | Restricted |
| `git_timeout` | 3600s | 300s | 300s |
| `max_repo_size_mb` | 5000 | 1000 | 1000 |

### 4. Pipeline Settings (`pipeline.*`)

Controls build pipeline execution.

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| `build_timeout` | 3600s | 2700s | 1800s |
| `max_concurrent_builds` | 1 | 2 | 3 |
| `workspace_cleanup_hours` | 1 | 12 | 24 |
| `max_output_size_mb` | 1000 | 750 | 500 |

### 5. Logging Settings (`logging.*`)

Controls application logging behavior.

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| `log_level` | DEBUG | INFO | WARNING |
| `log_format` | text | json | json |
| `enable_structured_logging` | False | True | True |
| `log_file` | console | optional | required |

### 6. API Settings (`api.*`)

Controls API behavior and limits.

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| `max_request_size_mb` | 1000 | 100 | 100 |
| `default_page_size` | 50 | 50 | 20 |
| `max_page_size` | 1000 | 100 | 100 |

## Environment Variables

All settings can be overridden using environment variables with the `__` (double underscore) delimiter.

### Examples:

```bash
# Override database URL for any environment
DATABASE_URL=postgresql://user:pass@localhost/mydb

# Override specific security setting
SECURITY__CORS_ORIGINS=["https://myapp.com", "https://admin.myapp.com"]

# Override multiple nested settings
SECURITY__RATE_LIMIT_ENABLED=false
SECURITY__RATE_LIMIT_REQUESTS=200
```

### Priority Order:

1. Environment variables (highest priority)
2. Environment-specific settings (DevSettings, StagingSettings, ProductionSettings)
3. Base settings defaults (lowest priority)

## Implementation Details

### Settings Loading

The settings are loaded in `app/config/settings.py`:

```python
def create_settings() -> BaseSettings:
    """Create appropriate settings instance based on environment."""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "staging":
        return StagingSettings()
    else:
        return DevSettings()  # Default
```

### Database Initialization

Database table creation is handled based on the `auto_create_tables` setting:

```python
def init_database() -> None:
    """Initialize database tables based on environment settings."""
    if settings.database.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    else:
        # Use Alembic migrations
```

### Security Validation

Services check environment-specific security settings:

```python
# Git host validation
if not settings.git.allow_any_git_host:
    if host not in settings.git.allowed_git_hosts:
        raise ValidationError("Git host not allowed")

# Encryption key requirements
if settings.security.require_encryption_key and not encryption_key:
    raise ConfigurationError("Encryption key required")
```

## Best Practices

### Development

1. Use the default development settings
2. Override specific settings only when needed
3. Keep sensitive data in environment variables

### Staging

1. Use staging-specific configuration
2. Test all production-like features
3. Validate security measures work correctly

### Production

1. Always set `ENVIRONMENT=production`
2. Provide strong encryption keys
3. Configure proper CORS origins
4. Enable all security features
5. Use structured logging for monitoring

### Security Considerations

1. **Never use development settings in production**
2. **Always provide strong encryption keys in production**
3. **Restrict CORS origins to specific domains**
4. **Enable rate limiting in production**
5. **Use structured logging for security monitoring**
6. **Regularly rotate secrets and encryption keys**

## Migration Guide

### From Legacy Settings

The legacy settings system is still supported through the `app.config` module. To migrate:

1. Update imports from `app.config` to `app.config.settings`
2. Update environment variable names to use `__` delimiter
3. Test with different environment settings

### Example Migration:

```python
# Old way
from app.config import get_settings
settings = get_settings()
database_url = settings.database_url

# New way
from app.config.settings import get_settings
settings = get_settings()
database_url = settings.database.database_url
```

## Testing

Use the provided test script to verify settings work correctly:

```bash
python test_tiered_settings.py
```

This script tests all three environments and verifies that:
- Correct settings are loaded for each environment
- Environment-specific overrides work
- Nested settings are properly configured

## Troubleshooting

### Common Issues

1. **Settings not loading correctly**
   - Check if `ENVIRONMENT` variable is set correctly
   - Verify environment variables use `__` delimiter
   - Check for typos in variable names

2. **Security errors in production**
   - Ensure `ENVIRONMENT=production` is set
   - Provide required encryption key
   - Configure proper CORS origins

3. **Database issues**
   - Check `auto_create_tables` setting
   - Verify database URL format
   - Ensure proper permissions for database operations

### Debug Mode

Enable detailed logging to troubleshoot settings:

```bash
LOGGING__LOG_LEVEL=DEBUG python -m app.main
```

This will show which settings are being loaded and from where.

## Conclusion

The tiered settings architecture provides a robust, secure, and flexible configuration system that adapts to different environments while maintaining security and performance. By following the guidelines and best practices outlined in this document, you can ensure your Open WebUI Customizer deployment is properly configured for any environment.