# TASK-07: Containerization & Deployment Appliance

## Overview
This task encompasses packaging `decide` into a self-contained, turnkey Docker appliance. It handles build-time baking of `fastino/GLiNER2.5-Decide` weights, container entrypoint scripting, directory and volume initialization (`/data`), and offline deployment verification.

## Module Architecture & Subtasks

| Subtask ID | Title | Target File | Description |
| :--- | :--- | :--- | :--- |
| **SUBTASK-7.1** | [Dockerfile & Build-Time Model Baking](file:///home/abhishek/decide/tasks/07-docker-and-deployment/01-dockerfile-build-time-baking.md) | `Dockerfile`<br/>`scripts/bake_model.py` | Multi-stage / optimized Dockerfile based on Python 3.11, downloading model weights during build to `/root/.cache/huggingface/`. |
| **SUBTASK-7.2** | [Entrypoint Script & Volume Mounts](file:///home/abhishek/decide/tasks/07-docker-and-deployment/02-container-entrypoint-and-volumes.md) | `entrypoint.sh` | Volume permission handling for `/data`, DB table initialization, admin seeding, and Uvicorn startup (1 worker). |
| **SUBTASK-7.3** | [Docker Compose & Offline Verification](file:///home/abhishek/decide/tasks/07-docker-and-deployment/03-docker-compose-and-offline-verification.md) | `docker-compose.yml`<br/>`tests/test_offline_boot.sh` | Production docker-compose file with `/data` volume, healthcheck probe, and script to verify offline zero-network execution. |

## Key Requirements (PRD Section 2.1 & 9)
- **Self-Contained Deployment:** Single `docker run` deployment with baked model weights.
- **Offline Guarantee:** Container must start and execute inference with zero internet access.
- **Persistent Volume:** `/data` volume for SQLite WAL files.
- **Container Readiness:** Boot to `/health` returning 200 OK in < 12 seconds.

## Acceptance Criteria
- [x] Dockerfile provides complete packaging with build-time model weight baking into `/root/.cache/huggingface/`.
- [x] Container entrypoint initializes target database volume directory, provisions schema, bootstraps admin, and runs Uvicorn.
- [x] Docker compose defines persistent volume, port mappings, and automatic healthcheck monitoring.
- [x] Offline verification script tests zero-network (`--network none`) boot and prediction readiness.

