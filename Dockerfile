FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    WORKERS=1 \
    DATABASE_PATH=/data/decide.db \
    HF_HUB_OFFLINE=1

# Install runtime system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and entrypoint
COPY decide ./decide
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Bake model weights into image layer
COPY scripts/bake_model.py ./scripts/
RUN HF_HUB_OFFLINE=0 python scripts/bake_model.py

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
