#!/usr/bin/env python3
"""
Entry point for the Open WebUI Customizer application.
This script initializes the database and starts the FastAPI application.
"""

import uvicorn
import argparse
import os

from app.main import app
from app.models.database import engine

def main():
    parser = argparse.ArgumentParser(description="Open WebUI Customizer")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to run the application on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the application on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
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