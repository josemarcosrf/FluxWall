# Dockerfile - Backend (FastAPI only, no frontend)
# Serves API at /api, health at /health, exports at /exports
# Build context: repository root (.)

# ─── Base image ──────────────────────────────────────────────────
FROM python:3.12-slim

# System dependencies for OpenCV, pillow-heif, ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libheif-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Backend deps (layer caching) - copy to /app/backend to match pyproject.toml paths
COPY backend/pyproject.toml backend/uv.lock backend/README.md /app/backend/
COPY backend/README.md /app/README.md
RUN cd /app/backend && uv sync --frozen --no-cache --no-dev

# Backend source + resources
COPY backend/src /app/backend/src
COPY backend/presets /app/backend/presets
COPY backend/assets /app/backend/assets
COPY backend/scripts /app/backend/scripts

WORKDIR /app/backend

# Expose port (Railway assigns $PORT)
ENV PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Bind to Railway-assigned $PORT (or default 8000 locally)
CMD ["sh", "-c", "uv run uvicorn fluxwall.main:app --host 0.0.0.0 --port ${PORT:-8000}"]