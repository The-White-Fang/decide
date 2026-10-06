#!/usr/bin/env bash
set -e

# Ensure persistence directory exists
DB_FILE="${DATABASE_PATH:-/data/decide.db}"
DATA_DIR=$(dirname "$DB_FILE")
mkdir -p "$DATA_DIR"

echo "================================================================================"
echo "                  STARTING DECIDE INFERENCE APPLIANCE                          "
echo "================================================================================"

# Initialize SQLite database schema and bootstrap admin credentials
python -m decide.bootstrap

echo "==> Launching FastAPI application on port ${PORT:-8000} (workers: ${WORKERS:-1})..."
exec uvicorn decide.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WORKERS:-1}" \
    --lifespan on
