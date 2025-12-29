"""
Logging Configuration for Flask App
====================================

Configure logging to both console and file with rotation.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(app):
    """
    Setup logging for Flask application.
    
    Logs will be written to:
    - Console (stdout) - for development
    - File (logs/app.log) - for persistence
    
    File rotation:
    - Max size: 10MB per file
    - Backup count: 5 files
    """
    # Create logs directory if not exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set log level based on environment
    log_level = logging.DEBUG if app.debug else logging.INFO
    log_level_console = logging.WARNING
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # File handler with rotation (10MB max, keep 5 backups)
    # Use delay=True to avoid file locking issues on Windows
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8',
        delay=True  # Defer file opening until first write (fixes Windows permission errors)
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level_console)
    console_handler.setFormatter(simple_formatter)
    
    # Configure root logger (for ALL modules including Flask app)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add handlers to root logger only (avoid duplication)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Configure Flask app logger (but don't add handlers - use root logger's)
    app.logger.setLevel(log_level)
    app.logger.propagate = True  # Ensure it uses root logger handlers
    
    # Log startup message
    app.logger.info("=" * 60)
    app.logger.info(f"Flask app started - Logging to logs/app.log")
    app.logger.info(f"Log level: {logging.getLevelName(log_level)}")
    app.logger.info("=" * 60)
    
    return app
