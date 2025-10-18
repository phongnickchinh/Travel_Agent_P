#!/bin/bash

echo "🚀 Starting Graduation Card Server..."

# Start Celery worker in the background
echo "📋 Starting Celery worker..."
celery -A celery_worker.celery worker --loglevel=info &

# Start Flask server (auto migrate will run on startup)
echo "🌐 Starting Flask server with auto-migrate..."
python run.py