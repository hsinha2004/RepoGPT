# RepoGPT — Production Deployment & Operations Guide

This guide describes the complete production deployment architecture, AWS EC2 provisioning, security hardening, automated deployments, backups, and disaster recovery procedures for **RepoGPT** per §16 and §17 of the specification.

---

## 1. Architecture Overview

In production, RepoGPT runs as a multi-container stack orchestrated via Docker Compose:

```
[ Internet / Clients ]
         │
    HTTPS: 443 / HTTP: 80
         ▼
┌────────────────────────────────────────────────────────┐
│  Caddy Web Server & TLS Terminator (caddy:2-alpine)    │
│  - Automated Let's Encrypt / ZeroSSL TLS certificates   │
│  - Reverse Proxy /api/* → api:8000 with SSE streaming   │
│  - Static Asset Delivery for Frontend SPA (Vite / React)│
│  - Security headers (HSTS, CSP, X-Frame-Options, etc.) │
└───────────────────────┬────────────────────────────────┘
                        │ internal network (edge)
                        ▼
┌────────────────────────────────────────────────────────┐
│  RepoGPT FastAPI Application (repogpt-api, UID 10001)   │
│  - Read-only root filesystem, tmpfs on /tmp            │
│  - Dropped Linux capabilities (cap_drop: ALL)          │
│  - No new privileges security flag                     │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
                ▼ internal network (data)▼
┌───────────────────────────────┐ ┌──────────────────────┐
│  Celery Worker (repogpt-worker)│ │ ChromaDB Vector Store│
│  - Ingestion, review, eval    │ │ - Local vector index │
└───────────────┬───────────────┘ └──────────────────────┘
                │
                ├────────────────────────┐
                ▼                        ▼
┌───────────────────────────────┐ ┌──────────────────────┐
│  MongoDB 8 (Metadata & State) │ │ Redis 7 (Cache/Queue)│
│  - Authenticated internal DB  │ │ - Password protected │
└───────────────────────────────┘ └──────────────────────┘
```

---

## 2. Infrastructure & Sizing Recommendations

### Recommended AWS EC2 Instances (Ubuntu 24.04 LTS)

| Instance Type | vCPU | RAM | Profile / Use Case | Cost Consideration |
|---|---|---|---|---|
| **`m7i-flex.large`** *(Recommended)* | 2 | 8 GB | Standard Full Stack (Local FastEmbed, Celery, Chroma, Mongo, Redis) | Free-tier eligible for new AWS accounts (credit-based); ~$0.0806/hr |
| **`c7i-flex.large`** | 2 | 4 GB | Balanced Stack (with 4 GB Swap enabled) | Cost-effective compute-optimized instance |
| **`t3.small`** | 2 | 2 GB | Lite Stack (Cloud embeddings: Gemini/OpenAI; 4 GB Swap) | Low burstable baseline |
| **`t2.micro` / `t3.micro`** | 1–2 | 1 GB | Minimal Demo / Lite (Swap required, API embeddings only) | Standard Free Tier; stop when idle |

> [!WARNING]
> **Cost Advisory:** Always stop EC2 instances when not in use during development and evaluation to preserve cloud credits and avoid unexpected charges.

---

## 3. AWS Network & Security Group Setup

Configure your AWS EC2 Security Group with the following inbound rules:

| Type | Protocol | Port Range | Source | Purpose |
|---|---|---|---|---|
| **SSH** | TCP | `22` | `YOUR_ADMIN_IP/32` | Secure administrative terminal access |
| **HTTP** | TCP | `80` | `0.0.0.0/0` | HTTP traffic (redirects to HTTPS via Caddy) |
| **HTTPS** | TCP | `443` | `0.0.0.0/0` | Secure web application traffic |

> [!IMPORTANT]
> **Never publish database ports (27017, 6379, 8000) to the public internet.** In production (`docker-compose.prod.yml`), all database and backend services communicate exclusively over internal Docker networks (`data` and `edge`).

---

## 4. Host Provisioning via Bootstrap Script

1. Launch an Ubuntu 24.04 LTS EC2 instance and attach an Elastic IP.
2. Connect to the instance:
   ```bash
   ssh -i your-key.pem ubuntu@YOUR_ELASTIC_IP
   ```
3. Clone or copy the deployment scripts and run the idempotent bootstrap script:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/repogpt/repogpt/main/deploy/ec2-bootstrap.sh -o ec2-bootstrap.sh
   sudo bash ec2-bootstrap.sh
   ```

The bootstrap script automatically:
- Installs unattended security updates, Docker Engine, Docker Compose, fail2ban, and UFW firewall.
- Allocates and mounts a 4 GB swap space (`/swapfile`).
- Creates a dedicated unprivileged user `repogpt` in the `docker` group.
- Sets up `/opt/repogpt` workspace and `/var/backups/repogpt`.

---

## 5. Application Deployment

### First-Time Deployment

1. Switch to the `repogpt` user and navigate to `/opt/repogpt`:
   ```bash
   cd /opt/repogpt
   ```
2. Copy `docker-compose.yml`, `docker-compose.prod.yml`, and `docker/` configuration folders to `/opt/repogpt`.
3. Create your production `.env` file from `.env.example`:
   ```bash
   python3 scripts/generate_secrets.py > .env
   chmod 600 .env
   ```
4. Set the following required variables in `.env`:
   ```bash
   ENVIRONMENT=production
   DOMAIN=repogpt.example.com          # Or your DuckDNS domain: myrepo.duckdns.org
   ACME_EMAIL=admin@example.com
   JWT_SECRET=<generated_by_script>
   ENCRYPTION_KEY=<generated_by_script>
   MONGO_ROOT_USER=root
   MONGO_ROOT_PASSWORD=<generated_secure_password>
   MONGO_APP_USER=repogpt
   MONGO_APP_PASSWORD=<generated_secure_password>
   REDIS_PASSWORD=<generated_secure_password>
   LLM_PROVIDER=gemini                 # Or anthropic, openai, groq, etc.
   GEMINI_API_KEY=AIzaSy...
   ```
5. Deploy using the zero-downtime deployment script:
   ```bash
   ./deploy/deploy.sh v1.0.0
   ```

The script automatically pulls the multi-arch images from GHCR, launches the containers, verifies health via `/api/v1/health/ready`, and rolls back if the health checks fail.

---

## 6. Continuous Deployment via GitHub Actions

The repository includes a production deployment workflow in `.github/workflows/deploy.yml`:
- Triggers on version tag pushes (`v*`) or manual workflow dispatch.
- Builds multi-arch Docker images (`linux/amd64`, `linux/arm64`) using Docker Buildx and pushes them to GitHub Container Registry (`ghcr.io`).
- Securely connects to your EC2 instance via SSH and executes `./deploy/deploy.sh <tag>`.

### Required GitHub Repository Secrets
- `EC2_HOST`: Elastic IP or public DNS hostname of your EC2 instance.
- `EC2_USER`: Deploy user (`repogpt`).
- `EC2_SSH_KEY`: Private SSH key configured for the deploy user.

---

## 7. Backups and Disaster Recovery

### Automated Daily Backups

Add the backup script to root crontab:
```bash
sudo crontab -e
```
Add the following line to schedule backups daily at 02:00 UTC:
```cron
0 2 * * * cd /opt/repogpt && ./deploy/backup.sh >> /var/log/repogpt_backup.log 2>&1
```

The backup script:
- Creates a timestamped directory `/var/backups/repogpt/YYYYMMDD_HHMMSS/`.
- Executes `mongodump --archive --gzip` with credentials.
- Tarballs the ChromaDB vector index and repository snapshot storage.
- Automatically deletes archives older than 7 days.
- Optionally syncs backups to an Amazon S3 bucket if `BACKUP_S3_BUCKET` is defined.

### Disaster Recovery & Restore Drill

To restore from a backup directory:
```bash
cd /opt/repogpt
./deploy/restore.sh /var/backups/repogpt/20261012_020000
```
The script will prompt for confirmation, drop and restore the MongoDB collections, restore ChromaDB and snapshot volumes, restart the API/Worker containers, and verify `/api/v1/health/ready`.

---

## 8. Alternative: Managed Database (MongoDB Atlas)

To use MongoDB Atlas instead of the self-hosted container:
1. In `.env`, set:
   ```bash
   MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/repogpt?retryWrites=true&w=majority
   ```
2. In Atlas, add your EC2 Elastic IP to the IP Access List.
3. In `docker-compose.prod.yml`, disable or comment out the `mongo` service.
