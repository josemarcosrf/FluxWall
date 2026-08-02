# Dockerfile - FluxWall (Railway single-image build)
# Builds the FastAPI backend AND bakes the compiled React SPA into it,
# so the backend serves the frontend at / (as code expects):
#   backend/src/fluxwall/main.py → base_dir.parent / 'frontend' / 'dist'
#
# Layout mirrors the repo:
#   /app/backend/...  (pyproject, src, presets, assets)
#   /app/frontend/dist (built SPA)

# ─── Stage 1: build the frontend ───────────────────────────────
FROM node:22-alpine AS frontend-build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ─── Stage 2: backend + baked SPA ──────────────────────────────
FROM python:3.12-slim

# System dependencies for OpenCV, pillow-heif, ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libheif-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Backend deps (layer caching)
COPY backend/pyproject.toml backend/uv.lock ./
RUN mkdir -p /app/backend && cp pyproject.toml uv.lock /app/backend/ && \
    cd /app/backend && uv sync --frozen --no-cache --no-dev

# Backend source + resources
COPY backend/src /app/backend/src
COPY backend/presets /app/backend/presets
COPY backend/assets /app/backend/assets
COPY backend/scripts /app/backend/scripts

# Baked frontend SPA
COPY --from=frontend-build /app/dist /app/frontend/dist

WORKDIR /app/backend

# Expose port (Railway assigns $PORT)
ENV PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "uvicorn", "fluxwall.main:app", "--host", "0.0.0.0", "--port", "8000"]