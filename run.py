#!/usr/bin/env python3
"""
Entry point for the Open WebUI Customizer application.
This script initializes the database and starts the FastAPI application.
"""

import uvicorn
import argparse
import os
import subprocess

from app.main import app
from app.models.database import engine

def main():
    parser = argparse.ArgumentParser(description="Open WebUI Customizer")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to run the application on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the application on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--skip-migrations", action="store_true", help="Skip running database migrations")

    args = parser.parse_args()

    # Run database migrations unless skipped
    if not args.skip_migrations:
        print("Running database migrations...")
        try:
            subprocess.run(["alembic", "upgrade", "head"], check=True, capture_output=True)
            print("Database migrations completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to run migrations: {e}")
            print("Use --skip-migrations to start without migrations")
            return

    # Start the application
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()