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

# MongoDB Atlas - no wait needed (cloud service)
echo "⚠️  Using MongoDB Atlas (cloud) - skipping local wait"

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
