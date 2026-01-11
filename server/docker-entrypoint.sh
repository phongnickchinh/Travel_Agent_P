#!/bin/bash
# ========================================
# Docker Entrypoint Script
# Runs database migrations before starting app
# Also handles database backup/restore
# ========================================

set -e

echo "========================================"
echo "Travel Agent P - Starting Application"
echo "========================================"

# Normalize DB name for all operations (honor both POSTGRES_DBNAME and POSTGRES_DB)
DB_NAME="${POSTGRES_DBNAME:-${POSTGRES_DB:-railway}}"

# ============= Database Backup Function =============
backup_database() {
    echo "📦 Creating database backup..."
    BACKUP_DIR="/backups"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"
    
    mkdir -p "$BACKUP_DIR"
    PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USERNAME" -d "$DB_NAME" -F c -b > "$BACKUP_FILE" 2>/dev/null || {
        echo "⚠️  Backup failed or database '$DB_NAME' not exists yet"
        return 0
    }
    
    echo "✅ Backup created: $BACKUP_FILE"
    
    # Keep only last 5 backups
    ls -t "$BACKUP_DIR"/backup_*.sql 2>/dev/null | tail -n +6 | xargs -r rm 2>/dev/null || true
}

# ============= Database Restore Function =============
restore_database() {
    BACKUP_FILE="/backups/phong.sql"
    
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "⚠️  No backup file found at $BACKUP_FILE (skip restore)"
        return 0
    fi
    
    echo "📦 Found backup file, checking if restore needed..."
    
    # Check if target database exists and has tables
    TABLE_COUNT=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USERNAME" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null || echo "0")
    TABLE_COUNT=$(echo "$TABLE_COUNT" | tr -d '[:space:]')
    
    if [ "$TABLE_COUNT" -gt "0" ]; then
        echo "✅ Database already has $TABLE_COUNT tables (skip restore)"
        return 0
    fi
    
    echo "🔄 Restoring database from backup..."
    
    # Restore from custom format backup (-C creates database from dump)
    # Using postgres as target to allow CREATE DATABASE from dump
    PGPASSWORD=$POSTGRES_PASSWORD pg_restore -h "$POSTGRES_HOST" -U "$POSTGRES_USERNAME" -C -d postgres --no-owner --no-privileges "$BACKUP_FILE" 2>&1 || {
        echo "⚠️  pg_restore completed with warnings (normal if objects already exist)"
    }
    
    echo "✅ Database restore completed!"
}

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USERNAME" -d postgres -c '\q' 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# Auto-restore database if needed (only on fresh deployment)
restore_database

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

echo "========================================"
echo "Starting Flask application..."
echo "========================================"

# Execute CMD from Dockerfile
exec "$@"
