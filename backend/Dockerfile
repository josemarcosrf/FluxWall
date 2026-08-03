# Dockerfile - FluxWall backend (FastAPI)
# Build context is the repo root (see docker-compose.yml); paths are repo-relative.
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

# Install Python dependencies first (layer caching).
# README.md must be present: backend/pyproject.toml declares readme = "../README.md".
COPY README.md backend/pyproject.toml backend/uv.lock ./
RUN mkdir -p /app/backend && cp pyproject.toml uv.lock /app/backend/ && \
    cd /app/backend && uv sync --frozen --no-cache --no-dev

# Copy application source and runtime resources
COPY backend/src /app/backend/src
COPY backend/presets /app/backend/presets
COPY backend/assets /app/backend/assets
COPY backend/scripts /app/backend/scripts

WORKDIR /app/backend

# Expose port (Railway assigns $PORT)
ENV PORT=8000
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "uvicorn", "fluxwall.main:app", "--host", "0.0.0.0", "--port", "8000"]