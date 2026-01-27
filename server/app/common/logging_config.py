"""
Logging Configuration for Flask App
====================================

Configure logging to both console and file with rotation.
Uses QueueHandler for non-blocking async logging to improve performance.
"""
import atexit
import logging
import os
import sys
import queue
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from pathlib import Path

# Global queue listener for cleanup
_queue_listener = None


def setup_logging(app):
    """
    Setup logging for Flask application with async file writes.
    
    Features:
    - QueueHandler for non-blocking logging (avoids I/O blocking)
    - RotatingFileHandler for file persistence with rotation
    - Console handler for development
    
    File rotation:
    - Max size: 10MB per file
    - Backup count: 5 files
    """
    global _queue_listener
    
    # Create logs directory if not exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set log level based on environment
    # PRODUCTION: INFO level (avoid DEBUG performance overhead)
    # DEVELOPMENT: DEBUG level for detailed tracing
    log_level = logging.DEBUG if app.debug else logging.INFO
    log_level_console = logging.INFO if app.debug else logging.WARNING
    
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
    
    # Create a queue for async logging (non-blocking I/O)
    log_queue = queue.Queue(-1)  # Unlimited size
    queue_handler = QueueHandler(log_queue)
    
    # QueueListener handles actual file/console writes in background thread
    _queue_listener = QueueListener(
        log_queue, 
        file_handler, 
        console_handler,
        respect_handler_level=True
    )
    _queue_listener.start()
    
    # Register cleanup on exit
    atexit.register(_queue_listener.stop)
    
    # Configure root logger (for ALL modules including Flask app)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add ONLY queue handler to root logger (writes go to background thread)
    root_logger.addHandler(queue_handler)
    
    # Configure Flask app logger (but don't add handlers - use root logger's)
    app.logger.setLevel(log_level)
    app.logger.propagate = True  # Ensure it uses root logger handlers
    
    # Log startup message
    app.logger.info("=" * 60)
    app.logger.info("Flask app started - Async logging to logs/app.log")
    app.logger.info("Log level: %s", logging.getLevelName(log_level))
    app.logger.info("=" * 60)
    
    return app
