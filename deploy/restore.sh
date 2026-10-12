#!/usr/bin/env bash
# ==============================================================================
# RepoGPT — Production Restore Script (§17.2)
# Restores MongoDB, ChromaDB, and repository storage from an archive directory.
# Usage: ./deploy/restore.sh /var/backups/repogpt/YYYYMMDD_HHMMSS
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${1:-}"

if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
  echo "Error: You must provide a valid backup directory path." >&2
  echo "Usage: $0 /var/backups/repogpt/YYYYMMDD_HHMMSS" >&2
  exit 1
fi

echo "=========================================================="
echo " Starting RepoGPT Restore from ${BACKUP_DIR}"
echo " WARNING: This will overwrite active database and index data!"
echo "=========================================================="

read -r -p "Are you sure you want to proceed with restore? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Restore aborted by user."
  exit 0
fi

# 1. Restore MongoDB
MONGO_ARCHIVE="$(find "$BACKUP_DIR" -name "mongodb_*.gz" | head -n 1)"
if [ -n "$MONGO_ARCHIVE" ] && [ -f "$MONGO_ARCHIVE" ]; then
  echo "[1/3] Restoring MongoDB collections from ${MONGO_ARCHIVE}..."
  if [ -f .env ]; then
    # shellcheck disable=SC1091
    set -a; source .env; set +a
  fi
  MONGO_USER="${MONGO_ROOT_USER:-root}"
  MONGO_PASS="${MONGO_ROOT_PASSWORD:-rootpassword}"

  docker compose exec -T mongo mongorestore \
    --username "${MONGO_USER}" \
    --password "${MONGO_PASS}" \
    --authenticationDatabase admin \
    --drop \
    --archive --gzip < "${MONGO_ARCHIVE}"
  echo "MongoDB restore completed."
else
  echo "[1/3] No MongoDB archive found in ${BACKUP_DIR}. Skipping."
fi

# 2. Restore ChromaDB
CHROMA_ARCHIVE="$(find "$BACKUP_DIR" -name "chroma_*.tar.gz" | head -n 1)"
if [ -n "$CHROMA_ARCHIVE" ] && [ -f "$CHROMA_ARCHIVE" ]; then
  echo "[2/3] Restoring ChromaDB vector storage from ${CHROMA_ARCHIVE}..."
  CHROMA_VOL_PATH="$(docker volume inspect repogpt_chroma_data --format '{{ .Mountpoint }}' 2>/dev/null || docker volume inspect $(docker compose config --volumes | grep chroma) --format '{{ .Mountpoint }}' 2>/dev/null || echo '')"
  if [ -n "$CHROMA_VOL_PATH" ] && [ -d "$CHROMA_VOL_PATH" ]; then
    tar -xzf "${CHROMA_ARCHIVE}" -C "$CHROMA_VOL_PATH"
    echo "ChromaDB volume restored."
  fi
else
  echo "[2/3] No ChromaDB archive found. Skipping."
fi

# 3. Restore Repository Data
REPO_ARCHIVE="$(find "$BACKUP_DIR" -name "repos_*.tar.gz" | head -n 1)"
if [ -n "$REPO_ARCHIVE" ] && [ -f "$REPO_ARCHIVE" ]; then
  echo "[3/3] Restoring repository storage from ${REPO_ARCHIVE}..."
  REPO_VOL_PATH="$(docker volume inspect repogpt_repo_data --format '{{ .Mountpoint }}' 2>/dev/null || docker volume inspect $(docker compose config --volumes | grep repo_data) --format '{{ .Mountpoint }}' 2>/dev/null || echo '')"
  if [ -n "$REPO_VOL_PATH" ] && [ -d "$REPO_VOL_PATH" ]; then
    tar -xzf "${REPO_ARCHIVE}" -C "$REPO_VOL_PATH"
    echo "Repo storage restored."
  fi
else
  echo "[3/3] No repository archive found. Skipping."
fi

echo "=========================================================="
echo " Restarting application containers..."
docker compose restart api worker

echo " Verifying service readiness..."
sleep 5
curl -s http://localhost/api/v1/health/ready || echo "Please check logs if health endpoint is not responding immediately."
echo ""
echo " Restore operation complete!"
echo "=========================================================="
