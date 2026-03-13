# VPS Deployment Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the digital goods SaaS platform to a fresh Ubuntu VPS with a single command, using Docker Compose for all services.

**Architecture:** Three Docker services (PostgreSQL, Redis, Reflex web app with embedded bot) orchestrated by docker-compose.yml. A one-click deploy.sh script automates Docker installation, environment configuration, and service startup on a fresh Ubuntu server.

**Tech Stack:** Docker, Docker Compose, Python 3.12, Node.js 20, PostgreSQL 16, Redis 7, Reflex 0.8.x, uv

**Spec:** `docs/superpowers/specs/2026-03-13-vps-deployment-design.md`

---

## Chunk 1: Docker Build Files

### Task 1: Create .dockerignore

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: Create `.dockerignore` file**

```
.git
.gitignore
.venv
.web
.states
.claude
.agent
.pytest_cache
__pycache__
*.pyc
*.pyo
*.egg-info
*.zip
*.db
temp_decompile/
tests/
docs/
uploaded_files/
.env
.env.*
README.md
backend.zip
frontend.zip
```

- [ ] **Step 2: Commit**

```bash
git add .dockerignore
git commit -m "feat: add .dockerignore for Docker build"
```

---

### Task 2: Create Dockerfile

**Files:**
- Create: `Dockerfile`
- Reference: `pyproject.toml` (dependencies)
- Reference: `rxconfig.py` (Reflex config)
- Reference: `shared/config.py` (env vars)

- [ ] **Step 1: Create multi-stage Dockerfile**

```dockerfile
# ============================================================
# Stage 1: Builder — install Python deps + init Reflex frontend
# ============================================================
FROM python:3.12-slim AS builder

# Install Node.js 20 (needed by Reflex for frontend build)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock .python-version ./

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY rxconfig.py ./
COPY shared/ ./shared/
COPY bot/ ./bot/
COPY services/ ./services/
COPY test_reflex/ ./test_reflex/
COPY assets/ ./assets/

# Skip DB bootstrap during build (no PostgreSQL available)
ENV DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dummy
ENV REFLEX_SKIP_STARTUP_BOOTSTRAP=1

# Initialize Reflex (generates .web/ directory with Next.js project)
RUN uv run reflex init

# Install frontend dependencies in builder (for reproducible offline runtime)
RUN cd .web && npm install

# ============================================================
# Stage 2: Runtime — lean image with all runtime deps
# ============================================================
FROM python:3.12-slim

# Install Node.js 20 runtime (Reflex needs it to run Next.js server)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code and Reflex frontend (including node_modules from builder)
COPY --from=builder /app/pyproject.toml /app/uv.lock /app/.python-version ./
COPY --from=builder /app/rxconfig.py ./
COPY --from=builder /app/shared/ ./shared/
COPY --from=builder /app/bot/ ./bot/
COPY --from=builder /app/services/ ./services/
COPY --from=builder /app/test_reflex/ ./test_reflex/
COPY --from=builder /app/assets/ ./assets/
COPY --from=builder /app/.web/ ./.web/

# Activate venv via PATH (avoids uv run overhead in runtime)
ENV PATH="/app/.venv/bin:$PATH"

# Expose Reflex ports: 3000 (frontend), 8000 (backend API)
EXPOSE 3000 8000

# Default command: run Reflex in production mode
CMD ["reflex", "run", "--env", "prod"]
```

- [ ] **Step 2: Commit**

```bash
git add Dockerfile
git commit -m "feat: add multi-stage Dockerfile for Reflex app"
```

---

## Chunk 2: Docker Compose & Deploy Script

### Task 3: Create docker-compose.yml

**Files:**
- Create: `docker-compose.yml`
- Reference: `shared/config.py` (env var names)
- Reference: `.env.example` (env var template)

- [ ] **Step 1: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD:?DB_PASSWORD must be set in .env}
      POSTGRES_DB: reflex
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  web:
    build: .
    ports:
      - "3000:3000"
      - "8000:8000"
    env_file: .env
    volumes:
      - reflex_data:/app/.states      # Reflex internal state (SQLite)
      - uploaded_files:/app/uploaded_files  # Export files and uploads
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  pgdata:
  reflex_data:
  uploaded_files:
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose.yml with postgres, redis, web"
```

---

### Task 4: Create deploy.sh

**Files:**
- Create: `deploy.sh`
- Reference: `.env.example` (env var template)

- [ ] **Step 1: Create deploy.sh one-click deployment script**

```bash
#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# One-click VPS deployment script
# Usage: bash deploy.sh
# ============================================================

echo "========================================="
echo "  Digital Goods Platform - VPS Deploy"
echo "========================================="
echo ""

# ----------------------------------------------------------
# 1. Check root / sudo
# ----------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] Please run as root: sudo bash deploy.sh"
  exit 1
fi

# ----------------------------------------------------------
# 2. Install Docker if not present
# ----------------------------------------------------------
if ! command -v docker &> /dev/null; then
  echo "[*] Installing Docker..."
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  echo "[OK] Docker installed."
else
  echo "[OK] Docker already installed."
fi

# ----------------------------------------------------------
# 3. Collect configuration
# ----------------------------------------------------------
echo ""
echo "--- Configuration ---"

# BOT_TOKEN
read -rp "Enter your Telegram BOT_TOKEN: " BOT_TOKEN
if [[ ! "$BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
  echo "[WARNING] BOT_TOKEN format looks invalid. Expected: 123456:ABC-DEF..."
  read -rp "Continue anyway? (y/N): " confirm
  [[ "$confirm" != "y" && "$confirm" != "Y" ]] && exit 1
fi

# TRONGRID_API_KEY (optional)
read -rp "Enter TRONGRID_API_KEY (press Enter to skip): " TRONGRID_API_KEY

# Auto-generate secrets
DB_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
SECRET_KEY=$(openssl rand -base64 48 | tr -d '/+=' | head -c 64)

echo ""
echo "[OK] Configuration collected."

# ----------------------------------------------------------
# 4. Generate .env file
# ----------------------------------------------------------
cat > .env << ENVEOF
# Auto-generated by deploy.sh — $(date -Iseconds)

# App
APP_NAME=Digital Goods Platform
DEBUG=false

# Database (container internal network)
DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD}@postgres:5432/reflex
DB_PASSWORD=${DB_PASSWORD}

# Redis (container internal network)
REDIS_URL=redis://redis:6379/0

# Runtime backends
EXPORT_TASK_BACKEND=db
PUSH_QUEUE_BACKEND=db

# Telegram Bot
BOT_TOKEN=${BOT_TOKEN}

# USDT Payment
TRONGRID_API_KEY=${TRONGRID_API_KEY}
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t

# Security
SECRET_KEY=${SECRET_KEY}
ENVEOF

chmod 600 .env
echo "[OK] .env generated (permissions: 600)."

# ----------------------------------------------------------
# 5. Build and start services
# ----------------------------------------------------------
echo ""
echo "[*] Building Docker images (this may take a few minutes)..."
docker compose build

echo "[*] Starting services..."
docker compose up -d

# ----------------------------------------------------------
# 6. Wait for services to be healthy
# ----------------------------------------------------------
echo "[*] Waiting for services to be ready..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U postgres &> /dev/null; then
    break
  fi
  sleep 2
done

# Verify all services are running
echo ""
docker compose ps

# ----------------------------------------------------------
# 7. Output results
# ----------------------------------------------------------
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================="
echo "  Deployment Complete!"
echo "========================================="
echo ""
echo "  Web Admin:  http://${SERVER_IP}:3000"
echo "  API:        http://${SERVER_IP}:8000"
echo ""
echo "  Default login:"
echo "    Username: admin"
echo "    Password: admin123"
echo ""
echo "--- Useful Commands ---"
echo "  docker compose logs -f          # View all logs"
echo "  docker compose logs -f web      # View web logs"
echo "  docker compose restart web      # Restart web service"
echo "  docker compose down             # Stop all services"
echo "  docker compose up -d --build    # Rebuild and restart"
echo ""
echo "--- Backup Database ---"
echo "  docker compose exec postgres pg_dump -U postgres reflex > backup.sql"
echo ""
```

- [ ] **Step 2: Make deploy.sh executable**

```bash
chmod +x deploy.sh
```

- [ ] **Step 3: Commit**

```bash
git add deploy.sh
git commit -m "feat: add one-click VPS deploy script"
```

---

## Chunk 3: Testing & Validation

### Task 5: Local Docker Build Validation

This task validates the Docker setup locally before deploying to VPS.

- [ ] **Step 1: Verify .dockerignore excludes the right files**

```bash
# Check that .env is in .dockerignore
grep "^\.env" .dockerignore
```

Expected: `.env` and `.env.*` both listed.

- [ ] **Step 2: Test Docker build (dry run)**

```bash
docker compose build
```

Expected: Build completes without errors. If Node.js or Reflex init fails, check the Dockerfile stages.

- [ ] **Step 3: Test Docker Compose up**

```bash
# Create a minimal .env for local testing
cat > .env.test << 'EOF'
APP_NAME=Digital Goods Platform
DEBUG=true
DATABASE_URL=postgresql+asyncpg://postgres:testpass@postgres:5432/reflex
DB_PASSWORD=testpass
REDIS_URL=redis://redis:6379/0
EXPORT_TASK_BACKEND=db
PUSH_QUEUE_BACKEND=db
BOT_TOKEN=000000000:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
SECRET_KEY=test-secret-key-not-for-production
EOF

# Start with test env
docker compose --env-file .env.test up -d
```

Expected: All 3 services start. `docker compose ps` shows postgres, redis, web as "Up".

- [ ] **Step 4: Verify services are healthy**

```bash
# Check postgres
docker compose exec postgres pg_isready -U postgres

# Check redis
docker compose exec redis redis-cli ping

# Check web (wait up to 60s for Reflex to start)
for i in $(seq 1 12); do
  curl -s http://localhost:3000 > /dev/null && echo "Web OK" && break
  echo "Waiting for web... ($i)"
  sleep 5
done
```

Expected: postgres ready, redis PONG, web responds with HTML.

- [ ] **Step 5: Clean up test environment**

```bash
docker compose down -v
rm .env.test
```

- [ ] **Step 6: Final commit with any fixes**

```bash
git add -A
git commit -m "fix: adjust Docker config based on local validation"
```

Only commit if changes were needed. Skip if everything worked first try.

---

### Task 6: Update .env.example

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add Docker-specific notes to .env.example**

Add a comment block at the top of `.env.example` explaining Docker vs local values:

```
# Environment Configuration
# ========================
# For local development: use localhost/127.0.0.1
# For Docker deployment: deploy.sh auto-generates this file
#   - DATABASE_URL uses 'postgres' (container name) instead of localhost
#   - REDIS_URL uses 'redis' (container name) instead of localhost
#   - DB_PASSWORD is auto-generated
#   - SECRET_KEY is auto-generated
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add Docker deployment notes to .env.example"
```
