"""FastAPI route handlers."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from fluxwall.api.schemas import (
    ExportRequest,
    ExportStartResponse,
    GeneratorInfoResponse,
    HealthResponse,
    JobStatusResponse,
    PresetResponse,
    PreviewStartRequest,
    PreviewStartResponse,
)
from fluxwall.core import (
    ExportFormat,
    ExportOptions,
    GeneratorType,
    LivePhotoExporter,
    export_mov,
    export_video,
    preset_registry,
    settings,
)
from fluxwall.generators import registry
from fluxwall.generators.base import Generator, GeneratorParams

router = APIRouter()


# ─── Health ───────────────────────────────────────────────────────


@router.get('/health', response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status='healthy',
        version=settings.app_version,
        generators=registry.list_names(),
    )


# ─── Generators ───────────────────────────────────────────────────


@router.get('/generators', response_model=list[GeneratorInfoResponse])
async def list_generators() -> list[GeneratorInfoResponse]:
    """List all available generators with their schemas."""
    return [
        GeneratorInfoResponse(
            name=info.name,
            display_name=info.display_name,
            description=info.description,
            param_schema=info.param_schema,
            presets=info.presets,
        )
        for info in registry.get_all()
    ]


@router.get('/generators/{name}', response_model=GeneratorInfoResponse)
async def get_generator(name: str) -> GeneratorInfoResponse:
    """Get generator details by name."""
    info = registry.get_info(name)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generator '{name}' not found",
        )
    return GeneratorInfoResponse(
        name=info.name,
        display_name=info.display_name,
        description=info.description,
        param_schema=info.param_schema,
        presets=info.presets,
    )


# ─── Presets ──────────────────────────────────────────────────────


@router.get('/presets', response_model=list[PresetResponse])
async def list_presets(generator: GeneratorType | None = None) -> list[PresetResponse]:
    """List all presets, optionally filtered by generator."""
    all_presets = preset_registry.get_all()
    if generator:
        all_presets = [p for p in all_presets if p.generator == generator]
    return [PresetResponse.model_validate(p.model_dump()) for p in all_presets]


@router.get('/presets/{preset_id}', response_model=PresetResponse)
async def get_preset(preset_id: str) -> PresetResponse:
    """Get a specific preset by ID."""
    preset = preset_registry.get(preset_id)
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset '{preset_id}' not found",
        )
    return PresetResponse.model_validate(preset.model_dump())


# ─── Preview ──────────────────────────────────────────────────────


@router.post('/preview/start', response_model=PreviewStartResponse)
async def start_preview(request: PreviewStartRequest) -> PreviewStartResponse:
    """Start a preview session (MJPEG stream)."""
    generator = registry.get(request.generator)
    if not generator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generator '{request.generator}' not found",
        )

    # Validate params
    try:
        generator.validate_params(request.params)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameters: {e}',
        ) from None

    # Generate stream URL
    stream_url = (
        f'/api/preview/stream?generator={request.generator.value}&params={request.params}&fps={request.target_fps}'
    )
    ws_url = f'/ws/preview?generator={request.generator.value}&fps={request.target_fps}'

    # For now, just return the MJPEG URL (no job tracking needed for stateless preview)
    return PreviewStartResponse(
        job_id=UUID(int=0),  # Placeholder
        stream_url=stream_url,
        ws_url=ws_url,
    )


@router.get('/preview/stream')
async def preview_stream(
    generator: GeneratorType,
    params: str = Query(default='{}', description='JSON-encoded generator parameters'),
    fps: int = Query(default=15, ge=1, le=30),
) -> StreamingResponse:
    """MJPEG stream for real-time preview."""
    gen = registry.get(generator)
    if not gen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generator '{generator}' not found",
        )

    try:
        parsed_params: dict[str, Any] = json.loads(params)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid JSON in params: {e}',
        ) from None

    try:
        gen_params = gen.validate_params(parsed_params)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameters: {e}',
        ) from None

    gen_params.fps = fps
    gen_params.duration_sec = 60  # Long duration for continuous preview

    async def frame_generator() -> AsyncGenerator[bytes, None]:
        boundary = 'frame'
        for frame in gen.generate_frames(gen_params):
            # Encode frame as JPEG
            import cv2

            _, jpeg = cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])

            yield (
                (f'--{boundary}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n').encode()
                + jpeg.tobytes()
                + b'\r\n'
            )

            # Control frame rate
            await asyncio.sleep(1.0 / fps)

    return StreamingResponse(
        frame_generator(),
        media_type='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
        },
    )


# ─── Export ───────────────────────────────────────────────────────


@router.post('/export', response_model=ExportStartResponse)
async def start_export(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
) -> ExportStartResponse:
    return await _do_export(request, background_tasks)


async def _do_export(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
) -> ExportStartResponse:
    """Start an export job (video or Live Photo)."""
    generator = registry.get(request.generator)
    if not generator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generator '{request.generator}' not found",
        )

    try:
        params = generator.validate_params(request.params)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameters: {e}',
        ) from None

    # Apply export options
    params.fps = request.options.fps
    params.duration_sec = request.options.duration_sec
    iphone_res = getattr(request.options.iphone_model, 'resolution', (1290, 2796))
    res = iphone_res
    params.width = res[0]
    params.height = res[1]

    # For now, run synchronously (will add job queue later)
    import uuid

    job_id = uuid.uuid4()

    # Create output directory
    output_dir = settings.exports_dir / str(job_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    if request.options.format == ExportFormat.LIVE_PHOTO:
        # Schedule Live Photo export in background
        background_tasks.add_task(
            _export_live_photo_background,
            job_id,
            generator,
            params,
            request.options,
            output_dir,
        )
        download_url = f'/api/export/download/{job_id}.zip'
    else:
        # Schedule video export in background
        background_tasks.add_task(
            _export_video_background,
            job_id,
            generator,
            params,
            request.options,
            output_dir,
        )
        ext = request.options.format.value
        download_url = f'/api/export/download/{job_id}.{ext}'

    return ExportStartResponse(
        job_id=job_id,
        status_url=f'/api/export/status/{job_id}',
        download_url=download_url,
    )


async def _export_video_background(
    job_id: UUID,
    generator: Generator,
    params: GeneratorParams,
    options: ExportOptions,
    output_dir: Path,
) -> None:
    """Background task for video export."""
    output_path = output_dir / f'output.{options.format.value}'

    if options.format == ExportFormat.MOV:
        export_mov(generator.generate_frames(params), output_path, params.fps)
    else:
        export_video(generator.generate_frames(params), output_path, params.fps)


async def _export_live_photo_background(
    job_id: UUID,
    generator: Generator,
    params: GeneratorParams,
    options: ExportOptions,
    output_dir: Path,
) -> None:
    """Background task for Live Photo export."""
    exporter = LivePhotoExporter(
        output_dir,
        base_name=f'livephoto_{job_id.hex[:8]}',
        duration=options.duration_sec,
        fps=options.fps,
        width=params.width,
        height=params.height,
        quality=options.quality,
    )
    exporter.export_from_generator(generator.generate_frames(params), params.total_frames)


@router.get('/export/status/{job_id}', response_model=JobStatusResponse)
async def export_status(job_id: UUID) -> JobStatusResponse:
    """Get export job status."""
    # TODO: Implement job queue status tracking
    return JobStatusResponse(
        id=job_id,
        status='completed',
        progress=1.0,
        current_frame=0,
        total_frames=0,
        download_url=f'/api/export/download/{job_id}.mp4',
    )


@router.get('/export/download/{job_id}.{ext}')
async def export_download(job_id: UUID, ext: str) -> FileResponse:
    """Download exported file."""
    output_dir = settings.exports_dir / str(job_id)
    file_path = output_dir / f'output.{ext}'

    if not file_path.exists():
        # Try Live Photo zip
        zip_path = output_dir / f'livephoto_{job_id.hex[:8]}.zip'
        if zip_path.exists():
            file_path = zip_path
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Export not found or not ready',
            )

    return FileResponse(
        file_path,
        media_type='application/octet-stream',
        filename=file_path.name,
    )


# ─── Export from Preset ──────────────────────────────────────────


@router.post('/export/preset/{preset_id}', response_model=ExportStartResponse)
async def export_from_preset(
    preset_id: str,
    options: ExportOptions | None = None,
) -> ExportStartResponse:
    """Start export using a preset."""
    preset = preset_registry.get(preset_id)
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset '{preset_id}' not found",
        )

    if options is None:
        options = ExportOptions()

    return await _do_export(
        ExportRequest(
            generator=preset.generator,
            params=preset.params,
            options=options,
        ),
        BackgroundTasks(),
    )
