"""WebSocket handler for real-time frame streaming."""

from __future__ import annotations

import asyncio
import base64
import contextlib

import cv2
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from fluxwall.core.models import GeneratorParams, GeneratorType
from fluxwall.generators.registry import registry

router = APIRouter(prefix='/ws', tags=['websocket'])


class PreviewSession:
    """Active preview session for WebSocket streaming."""

    def __init__(
        self,
        websocket: WebSocket,
        generator_type: GeneratorType,
        params: GeneratorParams,
        target_fps: int = 15,
        quality: int = 80,
    ):
        self.websocket = websocket
        self.generator_type = generator_type
        self.params = params
        self.target_fps = target_fps
        self.quality = quality
        self.running = False
        self.frame_idx = 0

        self.generator = registry.get(generator_type.value)
        if not self.generator:
            raise ValueError(f'Unknown generator: {generator_type}')

    async def run(self) -> None:
        """Main streaming loop."""
        self.running = True
        frame_interval = 1.0 / self.target_fps

        try:
            assert self.generator is not None

            # Send start confirmation
            await self.websocket.send_json(
                {
                    'type': 'started',
                    'generator': self.generator_type.value,
                    'target_fps': self.target_fps,
                    'total_frames': self.params.total_frames,
                }
            )

            for frame in self.generator.generate_frames(self.params):
                if not self.running:
                    break

                # Encode frame as JPEG
                _, jpeg = cv2.imencode(
                    '.jpg',
                    cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, self.quality],
                )

                # Send as base64
                await self.websocket.send_json(
                    {
                        'type': 'frame',
                        'frame_idx': self.frame_idx,
                        'timestamp': self.frame_idx / self.params.fps,
                        'data': base64.b64encode(jpeg.tobytes()).decode('ascii'),
                    }
                )

                self.frame_idx += 1

                # Control frame rate
                await asyncio.sleep(frame_interval)

        except WebSocketDisconnect:
            pass
        except Exception as e:
            with contextlib.suppress(Exception):
                await self.websocket.send_json(
                    {
                        'type': 'error',
                        'message': str(e),
                    }
                )
        finally:
            self.running = False

    async def update_params(self, params: dict) -> None:
        """Update generator parameters mid-stream."""
        # Create new params object
        for key, value in params.items():
            setattr(self.params, key, value)
        # Restart frame counter
        self.frame_idx = 0

    def stop(self) -> None:
        """Stop the streaming loop."""
        self.running = False


# Active sessions
active_sessions: dict[str, PreviewSession] = {}


@router.websocket('/preview/{session_id}')
async def websocket_preview(
    websocket: WebSocket,
    session_id: str,
    generator: str = 'mandelbrot',
    fps: int = 15,
    quality: int = 80,
) -> None:
    """WebSocket endpoint for real-time frame streaming.

    Protocol:
    - Client connects: ws://host/ws/preview/{session_id}?generator=mandelbrot&fps=15
    - Server sends: { "type": "started", ... }
    - Server streams: { "type": "frame", "frame_idx": N, "timestamp": T, "data": "base64..." }
    - Client can send: { "type": "update_params", "params": {...} }
    - Client can send: { "type": "stop" }
    """
    await websocket.accept()

    try:
        # Parse generator type
        gen_type = GeneratorType(generator)
    except ValueError:
        await websocket.send_json(
            {
                'type': 'error',
                'message': f'Unknown generator: {generator}',
            }
        )
        await websocket.close()
        return

    # Create default params
    params = GeneratorParams(
        fps=fps,
        duration_sec=10.0,  # Long duration for live preview
    )

    # Create session
    session = PreviewSession(
        websocket=websocket,
        generator_type=gen_type,
        params=params,
        target_fps=fps,
        quality=quality,
    )

    active_sessions[session_id] = session

    # Run streaming loop
    try:
        await session.run()
    finally:
        active_sessions.pop(session_id, None)


@router.websocket('/preview')
async def websocket_preview_new(
    websocket: WebSocket,
) -> None:
    """WebSocket endpoint with parameter negotiation on connect."""
    await websocket.accept()

    try:
        # Wait for initial config
        config = await websocket.receive_json()

        generator = config.get('generator', 'mandelbrot')
        target_fps = config.get('fps', 15)
        quality = config.get('quality', 80)
        params_dict = config.get('params', {})

        try:
            gen_type = GeneratorType(generator)
        except ValueError:
            await websocket.send_json(
                {
                    'type': 'error',
                    'message': f'Unknown generator: {generator}',
                }
            )
            await websocket.close()
            return

        # Create params from dict
        params = GeneratorParams(**params_dict)

        session = PreviewSession(
            websocket=websocket,
            generator_type=gen_type,
            params=params,
            target_fps=target_fps,
            quality=quality,
        )

        await session.run()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        with contextlib.suppress(Exception):
            await websocket.send_json({'type': 'error', 'message': str(e)})
