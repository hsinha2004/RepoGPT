#!/usr/bin/env bash
# ==============================================================================
# RepoGPT — Remote Deployment & Zero-Downtime Healthcheck Script (§17.1, §17.2)
# Usage: ./deploy/deploy.sh <tag>
# ==============================================================================

set -euo pipefail

TAG="${1:-latest}"
PREV_TAG=""

if [ -f .current_tag ]; then
  PREV_TAG="$(cat .current_tag)"
fi

echo "=========================================================="
echo " Starting RepoGPT Deployment (Target Tag: ${TAG})"
echo "=========================================================="

export IMAGE_TAG="${TAG}"

# Ensure .env exists with correct permissions
if [ ! -f .env ]; then
  echo "Error: .env file missing in current directory $(pwd)." >&2
  exit 1
fi
chmod 600 .env

echo "[1/4] Pulling production images from container registry..."
if ! docker compose -f docker-compose.yml -f docker-compose.prod.yml pull; then
  echo "Error: Failed to pull images for tag ${TAG}" >&2
  exit 1
fi

echo "[2/4] Deploying containers with docker compose..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans

echo "[3/4] Waiting for services to pass readiness checks..."
MAX_RETRIES=30
RETRY_DELAY=2
READY=false

for i in $(seq 1 $MAX_RETRIES); do
  echo "Health check attempt $i/$MAX_RETRIES..."
  # Check readiness via internal Caddy or API port
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80/api/v1/health/ready || true)
  if [ "$HTTP_CODE" = "200" ]; then
    echo "Service reports READY (HTTP 200)."
    READY=true
    break
  fi
  sleep $RETRY_DELAY
done

if [ "$READY" = "true" ]; then
  echo "[4/4] Deployment SUCCESSFUL!"
  echo "${TAG}" > .current_tag
  docker image prune -f
  echo "=========================================================="
  exit 0
else
  echo "=========================================================="
  echo " Readiness check FAILED! Initiating automated rollback..." >&2
  docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail 100 api
  
  if [ -n "$PREV_TAG" ] && [ "$PREV_TAG" != "$TAG" ]; then
    echo "Rolling back to previous tag: ${PREV_TAG}" >&2
    export IMAGE_TAG="${PREV_TAG}"
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans
  fi
  
  exit 1
fi
