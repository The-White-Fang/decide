# SUBTASK-7.2: Container Entrypoint & Volume Mounts

## Parent Task
[TASK-07: Containerization & Deployment Appliance](file:///home/abhishek/decide/tasks/07-docker-and-deployment/index.md)

## Target Code Path
`entrypoint.sh`

## Objective
Implement the container bootstrap shell script to ensure volume mount directories exist with proper permissions, invoke database migration/initialization, trigger admin seeding, and launch Uvicorn with single-worker concurrency.

## Functional Requirements
1. **Filesystem & Volume Initialization (PRD Section 6.1 & 9.1):**
   - Ensure target directory for `DATABASE_PATH` exists (defaults to `/data`).
   - If missing, create `/data` (`mkdir -p /data`).
2. **Schema & Bootstrap Invocation:**
   - Execute internal CLI or python command:
     `python -m decide.cli bootstrap` (or equivalent python startup hook)
     - Initializes SQLite database tables.
     - Checks `users` count; creates admin user with provided `ADMIN_PASSWORD` or generates secure 24-character password and prints to stdout.
     - Honors `FORCE_ADMIN_RESET=true` if supplied.
3. **Uvicorn Server Launch (PRD Section 6.1 & 8):**
   - Bind host `0.0.0.0` and port `$PORT` (default 8000).
   - Enforce worker count from `$WORKERS` (default 1, to prevent GPU VRAM race conditions or out-of-memory).
   - Execute with `exec uvicorn decide.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}`.

## Interface & Schema
```bash
#!/usr/bin/env bash
set -e

DATA_DIR=$(dirname "${DATABASE_PATH:-/data/decide.db}")
mkdir -p "$DATA_DIR"

echo "==> Initializing decide persistence and security layer..."
python -m decide.bootstrap

echo "==> Starting decide API service on port ${PORT:-8000}..."
exec uvicorn decide.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WORKERS:-1}" \
    --lifespan on
```

## Acceptance Criteria
- [x] Script is executable (`chmod +x entrypoint.sh`).
- [x] Database path directory is created automatically when mounted from host.
- [x] Auto-generated admin password prints clearly in Docker logs.
- [x] Graceful termination signals (SIGTERM, SIGINT) pass directly to Uvicorn process.

