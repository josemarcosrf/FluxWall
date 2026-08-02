"""API request/response schemas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from fluxwall.core.models import ExportOptions, GeneratorType


class GeneratorInfoResponse(BaseModel):
    """Generator information for API listing."""

    name: str
    display_name: str
    description: str
    param_schema: dict[str, Any]
    presets: dict[str, dict[str, Any]]


class PresetResponse(BaseModel):
    """Preset information for API."""

    id: str
    generator: GeneratorType
    name: str
    description: str
    params: dict[str, Any]
    export: dict[str, Any]
    tags: list[str]
    version: int


class PreviewStartRequest(BaseModel):
    """Request to start a preview session."""

    generator: GeneratorType
    params: dict[str, Any]
    target_fps: int = Field(default=15, ge=1, le=30)


class PreviewStartResponse(BaseModel):
    """Response with preview job ID and stream URL."""

    job_id: UUID
    stream_url: str
    ws_url: str | None = None


class ExportRequest(BaseModel):
    """Request to start an export job."""

    generator: GeneratorType
    params: dict[str, Any]
    options: ExportOptions


class ExportStartResponse(BaseModel):
    """Response with export job ID."""

    job_id: UUID
    status_url: str
    download_url: str | None = None


class JobStatusResponse(BaseModel):
    """Export/preview job status."""

    id: UUID
    status: str
    progress: float = 0.0
    current_frame: int = 0
    total_frames: int = 0
    output_path: str | None = None
    error: str | None = None
    download_url: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = 'healthy'
    version: str
    generators: list[str]


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
