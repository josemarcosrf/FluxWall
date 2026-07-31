"""Preview package."""

from fluxwall.preview.mjpeg import router as mjpeg_router

# Preview routers for FastAPI
preview_routers = [mjpeg_router]

__all__ = ['preview_routers']
