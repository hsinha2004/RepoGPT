#!/usr/bin/env bash
# ==============================================================================
# RepoGPT — AWS EC2 Idempotent Host Bootstrap Script (§17.2)
# Target OS: Ubuntu 24.04 LTS (m7i-flex.large / c7i-flex.large / t3.small)
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo " Starting RepoGPT EC2 Host Bootstrap"
echo "=========================================================="

# 1. Root check
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root (use sudo)." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

# 2. System updates and essential tools
echo "[1/8] Updating package index and installing dependencies..."
apt-get update -y
apt-get upgrade -y
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  unattended-upgrades \
  ufw \
  fail2ban \
  git \
  tar \
  gzip

# 3. Configure Unattended Security Upgrades
echo "[2/8] Configuring automatic security updates..."
systemctl enable unattended-upgrades
systemctl start unattended-upgrades

# 4. Swap Configuration (4 GB swap file for safety on memory-constrained hosts)
echo "[3/8] Checking swap space..."
if [ ! -f /swapfile ] && [ "$(swapon --show | wc -l)" -le 1 ]; then
  echo "Creating 4 GB swapfile at /swapfile..."
  fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  if ! grep -q '/swapfile' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
  sysctl vm.swappiness=10
  echo 'vm.swappiness=10' >> /etc/sysctl.d/99-repogpt-swap.conf
  echo "Swap configured successfully."
else
  echo "Swap already configured."
fi

# 5. Official Docker Engine & Docker Compose Installation
echo "[4/8] Installing Docker Engine and Compose plugin..."
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.asc ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
fi

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

# 6. Non-root Deploy User Configuration
echo "[5/8] Creating and configuring non-root deploy user 'repogpt'..."
if ! id "repogpt" &>/dev/null; then
  useradd -m -s /bin/bash -g docker repogpt
  echo "User 'repogpt' created and added to docker group."
else
  usermod -aG docker repogpt
fi

# 7. Firewall (UFW) and Fail2ban Setup
echo "[6/8] Configuring UFW firewall and Fail2ban..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable

systemctl enable fail2ban
systemctl restart fail2ban

# 8. Application Directory & Permissions
echo "[7/8] Setting up application workspace at /opt/repogpt..."
mkdir -p /opt/repogpt /var/backups/repogpt
chown -R repogpt:docker /opt/repogpt /var/backups/repogpt
chmod 750 /opt/repogpt /var/backups/repogpt

echo "[8/8] Host bootstrap completed successfully!"
echo "=========================================================="
echo " Next steps:"
echo " 1. Copy repository files, docker-compose.yml, and .env to /opt/repogpt"
echo " 2. Ensure /opt/repogpt/.env permissions are 600"
echo " 3. Run: cd /opt/repogpt && ./deploy/deploy.sh <version_tag>"
echo "=========================================================="
