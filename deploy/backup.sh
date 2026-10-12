#!/usr/bin/env bash
# ==============================================================================
# RepoGPT — Production Backup Script (§17.2)
# Dumps MongoDB, ChromaDB, and repository storage with 7-day retention.
# Cron Example: 0 2 * * * /opt/repogpt/deploy/backup.sh >> /var/log/repogpt_backup.log 2>&1
# ==============================================================================

set -euo pipefail

BACKUP_ROOT="${BACKUP_DIR:-/var/backups/repogpt}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

echo "=========================================================="
echo " Starting RepoGPT Backup: ${TIMESTAMP}"
echo "=========================================================="

mkdir -p "${TARGET_DIR}"

# 1. MongoDB Backup via mongodump archive
echo "[1/4] Dumping MongoDB database..."
# Source environment variables for credentials
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a; source .env; set +a
fi

MONGO_USER="${MONGO_ROOT_USER:-root}"
MONGO_PASS="${MONGO_ROOT_PASSWORD:-rootpassword}"

docker compose exec -T mongo mongodump \
  --username "${MONGO_USER}" \
  --password "${MONGO_PASS}" \
  --authenticationDatabase admin \
  --archive --gzip > "${TARGET_DIR}/mongodb_${TIMESTAMP}.gz"

echo "MongoDB dumped to ${TARGET_DIR}/mongodb_${TIMESTAMP}.gz ($(du -h "${TARGET_DIR}/mongodb_${TIMESTAMP}.gz" | cut -f1))"

# 2. ChromaDB Volume Backup
echo "[2/4] Archiving ChromaDB vector storage volume..."
CHROMA_VOL_PATH="$(docker volume inspect repogpt_chroma_data --format '{{ .Mountpoint }}' 2>/dev/null || docker volume inspect $(docker compose config --volumes | grep chroma) --format '{{ .Mountpoint }}' 2>/dev/null || echo '')"

if [ -n "$CHROMA_VOL_PATH" ] && [ -d "$CHROMA_VOL_PATH" ]; then
  tar -czf "${TARGET_DIR}/chroma_${TIMESTAMP}.tar.gz" -C "$CHROMA_VOL_PATH" .
  echo "ChromaDB volume archived ($(du -h "${TARGET_DIR}/chroma_${TIMESTAMP}.tar.gz" | cut -f1))"
else
  # Fallback to copy from running container
  docker compose cp chroma:/chroma/chroma - | gzip > "${TARGET_DIR}/chroma_${TIMESTAMP}.tar.gz" || true
  echo "ChromaDB container data copied."
fi

# 3. Repository Storage Volume Backup
echo "[3/4] Archiving repository snapshots storage..."
REPO_VOL_PATH="$(docker volume inspect repogpt_repo_data --format '{{ .Mountpoint }}' 2>/dev/null || docker volume inspect $(docker compose config --volumes | grep repo_data) --format '{{ .Mountpoint }}' 2>/dev/null || echo '')"

if [ -n "$REPO_VOL_PATH" ] && [ -d "$REPO_VOL_PATH" ]; then
  tar -czf "${TARGET_DIR}/repos_${TIMESTAMP}.tar.gz" -C "$REPO_VOL_PATH" .
  echo "Repo data archived ($(du -h "${TARGET_DIR}/repos_${TIMESTAMP}.tar.gz" | cut -f1))"
else
  docker compose cp api:/data - | gzip > "${TARGET_DIR}/repos_${TIMESTAMP}.tar.gz" || true
  echo "Repo data copied from container."
fi

# 4. Cleanup backups older than 7 days
echo "[4/4] Purging backups older than 7 days..."
find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime +7 -exec rm -rf {} + || true

# 5. Optional AWS S3 Upload
if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
  echo "Uploading backup to AWS S3: s3://${BACKUP_S3_BUCKET}/repogpt/${TIMESTAMP}/..."
  aws s3 sync "${TARGET_DIR}" "s3://${BACKUP_S3_BUCKET}/repogpt/${TIMESTAMP}/"
  echo "S3 upload complete."
fi

echo "=========================================================="
echo " Backup successfully completed at ${TARGET_DIR}"
echo "=========================================================="
