#!/usr/bin/env python3
"""
Test script to verify tiered settings are working correctly.

This script tests different environment configurations to ensure
the tiered settings system works as expected.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path for proper imports
parent_dir = Path(__file__).parent
sys.path.insert(0, str(parent_dir))

def test_environment(environment_name: str, expected_settings: dict):
    """Test a specific environment configuration."""
    print(f"\n{'='*60}")
    print(f"Testing {environment_name.upper()} Environment")
    print(f"{'='*60}")
    
    # Set environment
    os.environ["ENVIRONMENT"] = environment_name
    
    # Import and test settings
    from app.config.settings import create_settings, reload_settings
    reload_settings()  # Reload to pick up new environment
    
    settings = create_settings()
    
    print(f"Environment: {settings.environment}")
    print(f"Debug: {settings.debug}")
    
    # Test database settings
    print(f"\n--- Database Settings ---")
    print(f"Database URL: {settings.database.database_url}")
    print(f"Echo: {settings.database.echo}")
    if hasattr(settings.database, 'auto_create_tables'):
        print(f"Auto-create tables: {settings.database.auto_create_tables}")
    
    # Test security settings
    print(f"\n--- Security Settings ---")
    print(f"Secret key: {'*' * len(settings.security.secret_key)}")
    print(f"Require encryption key: {getattr(settings.security, 'require_encryption_key', 'N/A')}")
    print(f"CORS origins: {settings.security.cors_origins}")
    print(f"Rate limit enabled: {settings.security.rate_limit_enabled}")
    print(f"Detailed errors: {getattr(settings.security, 'detailed_errors', 'N/A')}")
    
    # Test git settings
    print(f"\n--- Git Settings ---")
    print(f"Git timeout: {settings.git.git_timeout}")
    print(f"Max repo size: {settings.git.max_repo_size_mb} MB")
    print(f"Allow any git host: {getattr(settings.git, 'allow_any_git_host', 'N/A')}")
    print(f"Allowed hosts: {settings.git.allowed_git_hosts}")
    
    # Test logging settings
    print(f"\n--- Logging Settings ---")
    print(f"Log level: {settings.logging.log_level}")
    print(f"Log format: {settings.logging.log_format}")
    print(f"Structured logging: {settings.logging.enable_structured_logging}")
    
    # Verify expected settings
    print(f"\n--- Verification ---")
    all_good = True
    
    for key, expected_value in expected_settings.items():
        parts = key.split('.')
        actual_value = settings
        
        try:
            for part in parts:
                actual_value = getattr(actual_value, part)
            
            if actual_value == expected_value:
                print(f"✓ {key}: {actual_value}")
            else:
                print(f"✗ {key}: expected {expected_value}, got {actual_value}")
                all_good = False
        except Exception as e:
            print(f"✗ {key}: error accessing - {str(e)}")
            all_good = False
    
    return all_good

def main():
    """Run all environment tests."""
    print("Tiered Settings Test Suite")
    print("Testing the Open WebUI Customizer configuration system")
    
    # Store original environment
    original_env = os.environ.get("ENVIRONMENT", "development")
    
    try:
        # Test development environment
        dev_expected = {
            "environment": "development",
            "debug": True,
            "database.echo": True,
            "database.auto_create_tables": True,
            "security.require_encryption_key": False,
            "security.cors_origins": ["*"],
            "security.rate_limit_enabled": False,
            "security.detailed_errors": True,
            "git.allow_any_git_host": True,
            "git.git_timeout": 3600,
            "logging.log_level": "DEBUG",
            "logging.log_format": "text",
            "logging.enable_structured_logging": False
        }
        
        dev_ok = test_environment("development", dev_expected)
        
        # Test staging environment
        staging_expected = {
            "environment": "staging",
            "debug": False,
            "database.echo": False,
            "database.auto_create_tables": True,
            "security.require_encryption_key": False,
            "security.cors_origins": ["https://staging.example.com", "http://localhost:3000"],
            "security.rate_limit_enabled": True,
            "security.detailed_errors": True,
            "git.allow_any_git_host": False,
            "git.git_timeout": 300,
            "logging.log_level": "INFO",
            "logging.log_format": "json",
            "logging.enable_structured_logging": True
        }
        
        staging_ok = test_environment("staging", staging_expected)
        
        # Test production environment
        prod_expected = {
            "environment": "production",
            "debug": False,
            "database.echo": False,
            "database.auto_create_tables": False,
            "security.require_encryption_key": True,
            "security.cors_origins": [],
            "security.rate_limit_enabled": True,
            "security.detailed_errors": False,
            "git.allow_any_git_host": False,
            "git.git_timeout": 300,
            "logging.log_level": "WARNING",
            "logging.log_format": "json",
            "logging.enable_structured_logging": True
        }
        
        prod_ok = test_environment("production", prod_expected)
        
        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Development: {'PASS' if dev_ok else 'FAIL'}")
        print(f"Staging: {'PASS' if staging_ok else 'FAIL'}")
        print(f"Production: {'PASS' if prod_ok else 'FAIL'}")
        
        overall = dev_ok and staging_ok and prod_ok
        print(f"\nOverall: {'ALL TESTS PASSED' if overall else 'SOME TESTS FAILED'}")
        
        return 0 if overall else 1
        
    finally:
        # Restore original environment
        os.environ["ENVIRONMENT"] = original_env

if __name__ == "__main__":
    sys.exit(main())