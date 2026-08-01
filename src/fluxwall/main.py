"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import Scope

from fluxwall.api.routes import router as api_router
from fluxwall.api.websocket import router as ws_router
from fluxwall.core import init_job_queue, load_presets, settings
from fluxwall.core.job_queue import shutdown_job_queue
from fluxwall.generators import discover_generators


class SPAStaticFiles(StaticFiles):
    """StaticFiles that falls back to ``index.html`` for unknown paths.

    Lets the React router (browser history) handle client-side routes like
    ``/studio`` while still serving hashed assets from the built ``dist``.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response('index.html', scope)
            raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    discover_generators()
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    load_presets()
    await init_job_queue(settings.max_concurrent_jobs)

    yield

    # Shutdown
    await shutdown_job_queue()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title='FluxWall API',
        description='Parametric iOS Live Wallpaper Generator API',
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

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

    # Serve the built React webapp (SPA) at the root when present.
    # Registered last so /api, /health and /exports win over the catch-all.
    webapp_dist = settings.base_dir / 'webapp' / 'dist'
    if webapp_dist.exists():
        app.mount('/', SPAStaticFiles(directory=str(webapp_dist), html=True), name='webapp')

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
