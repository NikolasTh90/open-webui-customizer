"""
Database configuration and initialization for Open WebUI Customizer.

This module provides database connection setup and session management
with support for tiered environments and auto table creation.
"""

import os
from typing import Generator
from urllib.parse import urlparse

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Import settings after parent directory is added to path
from app.config.settings import get_settings

# Get settings
settings = get_settings()

# Configure database engine based on settings
database_url = settings.database.database_url

# SQLite-specific configuration
if database_url.startswith("sqlite"):
    # Create the database directory if it doesn't exist
    parsed_url = urlparse(database_url)
    db_path = parsed_url.path[1:]  # Remove leading slash
    
    if db_path:
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    # SQLite connection arguments
    connect_args = {"check_same_thread": False}
    
    # Enable WAL mode for better concurrency
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    
    # Create engine with appropriate settings
    engine = create_engine(
        database_url,
        connect_args=connect_args,
        echo=settings.database.echo,
        poolclass=StaticPool,
        pool_pre_ping=True
    )
else:
    # PostgreSQL/MySQL configuration
    engine = create_engine(
        database_url,
        echo=settings.database.echo,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_timeout=settings.database.pool_timeout,
        pool_recycle=settings.database.pool_recycle,
        pool_pre_ping=True
    )

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for declarative models
Base = declarative_base()

def init_database() -> None:
    """
    Initialize database tables based on environment settings.
    
    In development and staging, tables are created automatically.
    In production, Alembic migrations should be used.
    """
    if hasattr(settings.database, 'auto_create_tables') and settings.database.auto_create_tables:
        # Import all models to ensure they're registered with Base
        from app.models import (
            branding, configuration, pipeline, registry,
            credential, git_repository, enhanced_pipeline
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print(f"Database tables created automatically for {settings.environment} environment")
    else:
        print("Database table creation skipped - using Alembic migrations")

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_db_session() -> Session:
    """
    Create a new database session.
    
    Returns:
        Session: SQLAlchemy database session
    """
    return SessionLocal()

# Initialize database on module import
init_database()