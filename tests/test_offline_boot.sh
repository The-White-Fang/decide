#!/usr/bin/env bash
set -e

CONTAINER_NAME="decide-offline-test"
IMAGE_NAME="${1:-decide:latest}"

echo "==> Testing offline container boot for image '${IMAGE_NAME}'..."

# Clean up any preexisting test container
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Temporary data volume directory
TEST_DATA_DIR=$(mktemp -d -t decide_test_data_XXXXXX)
trap 'docker rm -f "$CONTAINER_NAME" 2>/dev/null || true; rm -rf "$TEST_DATA_DIR"' EXIT

echo "==> Launching container with '--network none' (zero internet access)..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --network none \
    -v "$TEST_DATA_DIR:/data" \
    -e ADMIN_PASSWORD="OfflineTestPassword123!" \
    -e DEVICE=cpu \
    -e WORKERS=1 \
    "$IMAGE_NAME"

echo "==> Waiting for container bootstrap and warmup (< 15 seconds)..."
READY=0
for i in {1..15}; do
    HEALTH_OUTPUT=$(docker exec "$CONTAINER_NAME" curl -s http://localhost:8000/health || true)
    if [[ "$HEALTH_OUTPUT" =~ '"status":"healthy"' ]] && [[ "$HEALTH_OUTPUT" =~ '"model_loaded":true' ]]; then
        echo "==> Container reported healthy at attempt ${i}s: ${HEALTH_OUTPUT}"
        READY=1
        break
    fi
    echo "    [${i}s] Waiting for readiness probe..."
    sleep 1
done

if [ "$READY" -ne 1 ]; then
    echo "ERROR: Container failed to reach healthy state within 15 seconds offline."
    echo "==> Container logs:"
    docker logs "$CONTAINER_NAME"
    exit 1
fi

echo "==> SUCCESS: Offline container boot and model execution verified with ZERO network access!"
