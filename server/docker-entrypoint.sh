#!/bin/bash
# ========================================
# Docker Entrypoint Script
# Runs database migrations before starting app
# ========================================

set -e

echo "========================================"
echo "Travel Agent P - Starting Application"
echo "========================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USERNAME" -d "$POSTGRES_DBNAME" -c '\q' 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# Wait for MongoDB to be ready
echo "Waiting for MongoDB..."
# Use Python to check connection since mongosh might not be installed
until python -c "
import os, sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
try:
    uri = os.environ.get('MONGODB_URI')
    if not uri:
        print('MONGODB_URI is not set, skipping check.')
        sys.exit(0)
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    sys.exit(1)
" >/dev/null 2>&1; do
    echo "MongoDB is unavailable - sleeping"
    sleep 2
done
echo "✅ MongoDB is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis..."
until redis-cli -h "${REDIS_HOST:-localhost}" -p "${REDIS_PORT:-6379}" ping >/dev/null 2>&1; do
    echo "Redis is unavailable - sleeping"
    sleep 2
done
echo "✅ Redis is ready!"

# Run database migrations
echo "Running database migrations..."
flask db upgrade || {
    echo "⚠️  Migration failed, continuing anyway..."
}
echo "✅ Migrations completed!"

echo "========================================"
echo "Starting Flask application..."
echo "========================================"

# Execute CMD from Dockerfile
exec "$@"
