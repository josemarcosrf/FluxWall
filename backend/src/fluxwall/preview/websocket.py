"""WebSocket streaming preview (placeholder for future implementation)."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix='/ws', tags=['websocket'])


@router.websocket('/preview')
async def websocket_preview(websocket: WebSocket) -> None:
    """Binary WebSocket preview stream.

    Client protocol:
    - Connect: ws://host/ws/preview?generator=mandelbrot&fps=15
    - Send: {"type": "start", "params": {...}}
    - Send: {"type": "update", "params": {...}}
    - Send: {"type": "stop"}
    - Receive: binary JPEG frames with frame metadata as text messages
    """
    await websocket.accept()

    try:
        # Get initial params from query
        websocket.query_params.get('generator', 'mandelbrot')
        int(websocket.query_params.get('fps', '15'))

        while True:
            data = await websocket.receive_json()
            msg_type = data.get('type')

            if msg_type == 'start':
                # TODO: Implement frame generation with params
                await websocket.send_json(
                    {
                        'type': 'info',
                        'message': 'WebSocket preview not yet implemented - use MJPEG endpoint',
                    }
                )
            elif msg_type == 'stop':
                break
            elif msg_type == 'update':
                # Update parameters
                pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({'type': 'error', 'message': str(e)})
    finally:
        await websocket.close()
