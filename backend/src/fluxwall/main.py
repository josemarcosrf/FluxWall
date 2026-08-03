"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from fluxwall.api.routes import router as api_router
from fluxwall.api.websocket import router as ws_router
from fluxwall.core import init_job_queue, load_presets, settings
from fluxwall.core.job_queue import shutdown_job_queue
from fluxwall.core.logging import configure_logging
from fluxwall.generators import discover_generators

logger = logging.getLogger(__name__)

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    discover_generators()
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    load_presets()
    await init_job_queue(settings.max_concurrent_jobs)
    logger.info('Startup complete: version=%s debug=%s', settings.app_version, settings.debug)

    yield

    # Shutdown
    logger.info('Shutting down job queue and app')
    await shutdown_job_queue()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title='FluxWall API',
        description='Parametric iOS Live Wallpaper Generator API',
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=None if not settings.debug else '/docs',
        redoc_url=None if not settings.debug else '/redoc',
        openapi_url=None if not settings.debug else '/openapi.json',
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    # Global error handler: log anything that slips through unhandled.
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Inside an exception handler, so the traceback below is intended.
        logger.exception('Unhandled error on %s %s', request.method, request.url.path)  # noqa: LOG004
        return JSONResponse(status_code=500, content={'detail': 'Internal server error'})

    # Include routers
    app.include_router(api_router, prefix='/api')
    app.include_router(ws_router)

    # Health check (no prefix)
    @app.get('/health')
    async def health() -> dict[str, Any]:
        return {'status': 'healthy', 'version': settings.app_version}

    # Static files for exports (optional)
    app.mount(
        '/exports',
        StaticFiles(directory=str(settings.exports_dir), check_dir=False),
        name='exports',
    )

    return app


app = create_app()


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        'fluxwall.main:app',
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers,
    )
