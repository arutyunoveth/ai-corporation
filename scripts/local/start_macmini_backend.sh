#!/usr/bin/env zsh
set -euo pipefail

# =============================================================================
# start_macmini_backend.sh
# Build and start AI-Corporation backend Docker container for Mac mini pilot
# Listens ONLY on 127.0.0.1:PORT — NOT exposed to network
# =============================================================================

SCRIPT_DIR="${0:a:h}"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME_DIR="$HOME/arvectum-runtime"
LOG_DIR="$RUNTIME_DIR/logs"
PID_FILE="$RUNTIME_DIR/backend.pid"

BACKEND_PORT="${BACKEND_PORT:-8001}"
DOCKER_IMAGE="${DOCKER_IMAGE:-arvectum-pilot:macmini}"
CONTAINER_NAME="${CONTAINER_NAME:-arvectum-pilot}"
ENV_FILE="${ENV_FILE:-${PROJECT_ROOT}/.env.macmini.local}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: Env file not found at $ENV_FILE"
    echo "Copy .env.macmini.example to .env.macmini.local and fill in secrets."
    exit 1
fi

echo "Building Docker image..."
docker build -t "$DOCKER_IMAGE" "$PROJECT_ROOT"

echo "Stopping old container..."
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "Starting backend container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --env-file "$ENV_FILE" \
    -v "${PROJECT_ROOT}/data:/app/data" \
    -p "127.0.0.1:${BACKEND_PORT}:8000" \
    "$DOCKER_IMAGE"

echo "Container started."
docker ps --filter "name=$CONTAINER_NAME" --format "table {{.ID}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "Waiting for startup..."
sleep 5

if curl -sf "http://127.0.0.1:${BACKEND_PORT}/" > /dev/null 2>&1; then
    echo "SUCCESS: Backend is running at http://127.0.0.1:${BACKEND_PORT}"
else
    echo "WARNING: Container started but not yet responding. Check logs:"
    echo "  docker logs $CONTAINER_NAME"
fi
