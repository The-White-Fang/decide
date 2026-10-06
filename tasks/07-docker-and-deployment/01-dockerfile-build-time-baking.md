# SUBTASK-7.1: Dockerfile & Build-Time Model Baking

## Parent Task
[TASK-07: Containerization & Deployment Appliance](file:///home/abhishek/decide/tasks/07-docker-and-deployment/index.md)

## Target Code Path
`Dockerfile` and `scripts/bake_model.py`

## Objective
Create the container build recipe that packages Python 3.11, all runtime dependencies, application code, pre-compiled static assets, and pre-bakes the `fastino/GLiNER2.5-Decide` weights directly into the image filesystem.

## Functional Requirements
1. **Base Image & System Dependencies:**
   - Base image: `python:3.11-slim`.
   - Install essential system libraries (`curl`, `build-essential` if needed).
2. **Dependency Layering:**
   - Copy `pyproject.toml` / `requirements.txt` first to leverage Docker layer caching.
   - Install dependencies: `torch`, `gliner2`, `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic-settings`, `bcrypt`, `itsdangerous`, `jinja2`, `python-multipart`.
3. **Build-Time Model Baking (PRD Section 9.2):**
   - Create helper script `scripts/bake_model.py`:
     ```python
     from gliner2 import AutoExtractor
     AutoExtractor.from_pretrained("fastino/GLiNER2.5-Decide", cache_dir="/root/.cache/huggingface")
     ```
   - Run `python scripts/bake_model.py` during `docker build` layer execution.
   - Ensure the Hugging Face cache directory `/root/.cache/huggingface/` is retained in the final image layer.
4. **Application Code & Permissions:**
   - Copy application codebase `decide/`.
   - Copy and make executable `entrypoint.sh`.
   - Set environment variables (`PYTHONUNBUFFERED=1`, `HF_HUB_OFFLINE=1` at runtime).
   - Expose port `8000`.

## Interface & Schema
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake model weights into image layer
COPY scripts/bake_model.py ./scripts/
RUN python scripts/bake_model.py

COPY decide ./decide
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

VOLUME ["/data"]
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
```

## Acceptance Criteria
- [x] Image builds without errors.
- [x] Model weights reside inside `/root/.cache/huggingface/` within the image.
- [x] Starting the container with `--network none` starts successfully and serves predictions.

