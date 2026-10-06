# SUBTASK-7.3: Docker Compose & Offline Verification

## Parent Task
[TASK-07: Containerization & Deployment Appliance](file:///home/abhishek/decide/tasks/07-docker-and-deployment/index.md)

## Target Code Path
`docker-compose.yml` and `tests/test_offline_boot.sh`

## Objective
Provide sample Docker Compose manifests for CPU and GPU deployments, include container healthcheck declarations, and create an automated offline verification script to certify zero-network readiness.

## Functional Requirements
1. **Docker Compose Configuration (`docker-compose.yml`):**
   - Service definition `decide`.
   - Port mapping: `8000:8000`.
   - Volume mount: `decide_data:/data`.
   - Environment variable defaults with comments.
   - Built-in container healthcheck:
     ```yaml
     healthcheck:
       test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
       interval: 10s
       timeout: 5s
       retries: 3
       start_period: 15s
     ```
   - Optional GPU profile utilizing NVIDIA container toolkit (`deploy.resources.reservations.devices`).
2. **Offline Boot Verification Test (`tests/test_offline_boot.sh`):**
   - Starts container with `--network none` and a mounted volume.
   - Waits up to 15 seconds for boot.
   - Executes container-internal `curl http://localhost:8000/health` via `docker exec`.
   - Confirms `{"status": "healthy", "model_loaded": true}` is returned without external internet connectivity.

## Interface & Schema
```yaml
version: "3.8"

services:
  decide:
    build: .
    image: decide:latest
    container_name: decide-appliance
    ports:
      - "8000:8000"
    environment:
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=
      - FORCE_ADMIN_RESET=false
      - DEVICE=auto
      - WORKERS=1
    volumes:
      - decide_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 15s

volumes:
  decide_data:
```

## Acceptance Criteria
- [x] `docker compose up -d` successfully provisions container, database, and healthcheck.
- [x] Container reaches "healthy" status within 12 seconds.
- [x] Offline test script verifies model loads and functions without internet access.

