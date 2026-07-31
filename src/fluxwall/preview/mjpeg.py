"""MJPEG streaming preview endpoint."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import cv2
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from fluxwall.core.models import GeneratorParams, GeneratorType
from fluxwall.generators.registry import registry

router = APIRouter(prefix='/preview', tags=['preview'])


async def generate_mjpeg_stream(
    generator_type: GeneratorType,
    params: GeneratorParams,
    target_fps: int = 15,
    quality: int = 80,
    max_frames: int | None = None,
) -> StreamingResponse:
    """Generate MJPEG stream from generator."""
    generator = registry.get(generator_type.value)
    if not generator:
        raise HTTPException(404, f'Generator {generator_type.value} not found')

    frame_interval = 1.0 / target_fps
    frame_count = 0

    boundary = 'frame'

    async def frame_generator() -> AsyncGenerator[bytes, None]:
        nonlocal frame_count

        for frame in generator.generate_frames(params):
            if max_frames and frame_count >= max_frames:
                break

            # Encode as JPEG
            _, jpeg = cv2.imencode(
                '.jpg',
                cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_JPEG_QUALITY, quality],
            )

            yield (
                (f'--{boundary}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n').encode()
                + jpeg.tobytes()
                + b'\r\n'
            )

            frame_count += 1
            await asyncio.sleep(frame_interval)

    return StreamingResponse(
        frame_generator(),
        media_type=f'multipart/x-mixed-replace; boundary={boundary}',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        },
    )


@router.get('/stream')
async def mjpeg_preview(
    generator: str = Query(..., description='Generator name'),
    target_fps: int = Query(15, ge=1, le=60, description='Preview FPS'),
    quality: int = Query(80, ge=10, le=100, description='JPEG quality'),
    max_frames: int | None = Query(None, description='Max frames (None = infinite)'),
    # GeneratorParams fields
    width: int = Query(1170, ge=100, le=2000),
    height: int = Query(2532, ge=100, le=4000),
    fps: int = Query(30, ge=1, le=60),
    duration_sec: float = Query(60.0, ge=1.0, le=300.0),
    colormap: str = Query('magma'),
    seed: int | None = Query(None),
    # Generator-specific params passed as query string
    **extra_params: Any,
) -> StreamingResponse:
    """MJPEG preview stream.

    Usage in HTML:
    <img src="/api/preview/stream"
    "?generator=mandelbrot&width=1170&height=2532&fps=30"
    "&duration_sec=3&colormap=magma&center_x=-0.743"
    "&center_y=0.131&zoom=1000000">
    """
    try:
        gen_type = GeneratorType(generator)
    except ValueError:
        raise HTTPException(404, f'Unknown generator: {generator}') from None

    # Build params
    params_dict: dict[str, Any] = {
        'width': width,
        'height': height,
        'fps': fps,
        'duration_sec': duration_sec,
        'colormap': colormap,
        'seed': seed,
    }
    params_dict.update(extra_params)

    params = GeneratorParams(**params_dict)

    return await generate_mjpeg_stream(
        gen_type,
        params,
        target_fps=target_fps,
        quality=quality,
        max_frames=max_frames,
    )


@router.get('/frame')
async def single_frame(
    generator: str = Query(...),
    frame_idx: int = Query(0, ge=0),
    width: int = Query(1170),
    height: int = Query(2532),
    colormap: str = Query('magma'),
    **extra_params: Any,
) -> Response:
    """Get a single frame as JPEG."""
    try:
        gen_type = GeneratorType(generator)
    except ValueError:
        raise HTTPException(404, f'Unknown generator: {generator}') from None

    generator_obj = registry.get(gen_type.value)
    if not generator_obj:
        raise HTTPException(404, f'Generator {generator} not found')

    params = GeneratorParams(
        width=width,
        height=height,
        colormap=colormap,
        **extra_params,
    )

    frame = generator_obj.generate_frame(frame_idx, params)

    _, jpeg = cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])

    return Response(
        content=jpeg.tobytes(),
        media_type='image/jpeg',
        headers={'Cache-Control': 'no-cache'},
    )
