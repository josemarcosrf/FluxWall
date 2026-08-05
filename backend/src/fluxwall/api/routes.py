"""FastAPI route handlers."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
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
    FrameArray,
    GeneratorType,
    LivePhotoExporter,
    export_mov,
    export_video,
    preset_registry,
    settings,
)
from fluxwall.core.job_queue import Job, job_queue
from fluxwall.generators import registry
from fluxwall.generators.base import Generator, GeneratorParams

router = APIRouter()

logger = logging.getLogger(__name__)


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
async def start_export(request: ExportRequest) -> ExportStartResponse:
    return await _do_export(request)


def _progress_frames(
    frames: Iterator[FrameArray],
    job: Job,
    total_frames: int,
) -> Iterator[FrameArray]:
    """Wrap a frame iterator so progress/current_frame track the export."""

    def _emit(idx: int, frame: FrameArray) -> FrameArray:
        job.current_frame = idx + 1
        job.progress = min(1.0, (idx + 1) / max(1, total_frames))
        return frame

    for idx, frame in enumerate(frames):
        yield _emit(idx, frame)


def _run_export_task(
    generator: Generator,
    params: GeneratorParams,
    options: ExportOptions,
    job: Job,
) -> None:
    """Synchronous export runner — executed in a worker thread."""
    output_dir = settings.exports_dir / job.id
    output_dir.mkdir(parents=True, exist_ok=True)

    job.total_frames = params.total_frames
    frames = _progress_frames(generator.generate_frames(params), job, params.total_frames)

    if options.format == ExportFormat.LIVE_PHOTO:
        exporter = LivePhotoExporter(
            output_dir,
            base_name=f'livephoto_{job.id[:8]}',
            duration=options.duration_sec,
            fps=options.fps,
            width=params.width,
            height=params.height,
            quality=options.quality,
        )
        exporter.export_from_generator(frames, params.total_frames)
        zip_path = exporter.create_ios_import_package(
            output_dir,
            output_dir / f'livephoto_{job.id[:8]}.pvt',
        )
        job.output_path = str(zip_path)
        return

    output_path = output_dir / f'output.{options.format.value}'
    if options.format == ExportFormat.MOV:
        export_mov(frames, output_path, fps=params.fps, width=params.width, height=params.height)
    else:
        export_video(frames, output_path, fps=params.fps, width=params.width, height=params.height)
    job.output_path = str(output_path)
    logger.info(
        'Export completed: job_id=%s output=%s (%sx%s, %s frames)',
        job.id,
        output_path,
        params.width,
        params.height,
        params.total_frames,
    )


def _make_export_task(
    generator: Generator,
    params: GeneratorParams,
    options: ExportOptions,
) -> Callable[[Job], Awaitable[None]]:
    """Build the async task the job queue runs for this export."""

    async def run(job: Job) -> None:
        await asyncio.to_thread(_run_export_task, generator, params, options, job)

    return run


async def _do_export(request: ExportRequest) -> ExportStartResponse:
    """Start an export job (video or Live Photo) in the async job queue."""
    logger.info(
        'POST /export requested: generator=%s format=%s fps=%s duration=%s device=%s',
        request.generator,
        request.options.format.value,
        request.options.fps,
        request.options.duration_sec,
        request.options.iphone_model.value,
    )
    logger.debug('POST /export params=%s', request.params)

    generator = registry.get(request.generator)
    if not generator:
        logger.warning('POST /export rejected: generator %r not found', request.generator)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generator '{request.generator}' not found",
        )

    try:
        params = generator.validate_params(request.params)
        logger.debug('Generator %s valid: params=%s', request.generator, request.params)
    except Exception as e:
        logger.warning('POST /export rejected: generator=%s params validation failed: %s', request.generator, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameters: {e}',
        ) from None

    # Apply export options
    params.fps = request.options.fps
    params.duration_sec = request.options.duration_sec
    iphone_res = getattr(request.options.iphone_model, 'resolution', (1290, 2796))
    params.width, params.height = iphone_res

    job_id = job_queue.enqueue(
        generator=request.generator,
        params=request.params,
        options=request.options,
        task=_make_export_task(generator, params, request.options),
    )
    logger.info(
        'POST /export accepted: job_id=%s generator=%s format=%s',
        job_id,
        request.generator,
        request.options.format.value,
    )

    ext = request.options.format.value
    if request.options.format == ExportFormat.LIVE_PHOTO:
        ext = 'zip'

    return ExportStartResponse(
        job_id=UUID(job_id),
        status_url=f'/api/export/status/{job_id}',
        download_url=f'/api/export/download/{job_id}.{ext}',
    )


@router.get('/export/status/{job_id}', response_model=JobStatusResponse)
async def export_status(job_id: UUID) -> JobStatusResponse:
    """Get export job status from the job queue."""
    job = job_queue.get_status(str(job_id))
    if not job:
        logger.warning('GET /export/status: job %s not found', job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Export job not found',
        )

    download_url = None
    if job.output_path:
        suffix = Path(job.output_path).suffix.lstrip('.')
        if suffix:
            download_url = f'/api/export/download/{job_id}.{suffix}'

    return JobStatusResponse(
        id=job_id,
        status=job.status.value,
        progress=job.progress,
        current_frame=job.current_frame,
        total_frames=job.total_frames,
        output_path=job.output_path,
        error=job.error,
        download_url=download_url,
    )


@router.get('/export/download/{job_id}.{ext}')
async def export_download(job_id: UUID, ext: str) -> FileResponse:
    """Download an exported file once the job has produced it."""
    job = job_queue.get_status(str(job_id))
    if job and job.output_path:
        candidate = Path(job.output_path)
        if candidate.exists():
            return FileResponse(
                candidate,
                media_type='application/octet-stream',
                filename=candidate.name,
            )

    # Fallback: resolve by naming convention (jobs started before output_path existed)
    output_dir = settings.exports_dir / str(job_id)
    for name in (f'output.{ext}', f'livephoto_{job_id.hex[:8]}.zip'):
        candidate = output_dir / name
        if candidate.exists():
            return FileResponse(
                candidate,
                media_type='application/octet-stream',
                filename=candidate.name,
            )

    if job is None:
        logger.warning('GET /export/download: job %s not found', job_id)
    else:
        logger.warning('GET /export/download: job %s has no ready output (path=%s)', job_id, job.output_path)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='Export not found or not ready',
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
        )
    )
