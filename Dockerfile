# ============================================================
# Stage 1: Builder — install Python deps + init Reflex frontend
# ============================================================
FROM python:3.12-slim AS builder

# Install Node.js 20 (needed by Reflex for frontend build)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock .python-version README.md ./

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

# Install Node.js 20 runtime + unzip (Reflex needs Node.js for Next.js, unzip for bun)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip \
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
