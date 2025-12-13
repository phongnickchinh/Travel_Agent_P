#!/bin/bash

echo "🚀 Starting Graduation Card Server..."
# Start Celery worker in the background
echo "📋 Starting Celery worker..."
celery -A celery_worker.celery worker --loglevel=info &

# Start Flask server with Gunicorn (auto migrate will run on startup)
echo "🌐 Starting Flask server with Gunicorn..."
gunicorn run:app -b 0.0.0.0:${PORT:-5000} --workers=2 --threads=4 --timeout=120 --access-logfile - --error-logfile -