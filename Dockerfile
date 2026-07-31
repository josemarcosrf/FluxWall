# Dockerfile - FluxWall
FROM python:3.12-slim

# System dependencies for OpenCV, pillow-heif, ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libheif-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY presets ./presets
COPY assets ./assets

# Install dependencies
RUN uv sync --frozen --no-cache --no-dev

# Expose ports (Railway assigns $PORT)
ENV PORT=8000
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI (Streamlit runs as separate process in production)
CMD ["uv", "run", "uvicorn", "fluxwall.main:app", "--host", "0.0.0.0", "--port", "8000"]