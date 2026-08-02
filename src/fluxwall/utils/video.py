"""Video encoding utilities."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import cv2
import ffmpeg
import numpy as np
from numpy.typing import NDArray


def frames_to_video(
    frames: Iterator[NDArray[np.uint8]],
    output_path: str | Path,
    fps: int = 30,
    width: int | None = None,
    height: int | None = None,
    codec: str = 'mp4v',
    quality: int = 90,
) -> Path:
    """Write frames to video file using OpenCV.

    Args:
        frames: Iterator of RGB frames (H, W, 3)
        output_path: Output video path
        fps: Frames per second
        width: Video width (inferred from first frame if None)
        height: Video height (inferred from first frame if None)
        codec: FourCC codec (mp4v, avc1, h264, etc.)
        quality: Quality 0-100 (for some codecs)

    Returns:
        Path to output video
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frames_iter = iter(frames)
    first_frame = next(frames_iter)

    if width is None:
        width = first_frame.shape[1]
    if height is None:
        height = first_frame.shape[0]

    fourcc = cv2.VideoWriter_fourcc(*codec)  # type: ignore[attr-defined]
    writer = cv2.VideoWriter(
        str(output_path),
        fourcc,
        fps,
        (width, height),
    )

    # Write first frame
    if first_frame.shape[:2] != (height, width):
        first_frame = cv2.resize(first_frame, (width, height)).astype(np.uint8)
    writer.write(cv2.cvtColor(first_frame, cv2.COLOR_RGB2BGR))

    # Write remaining frames
    for frame in frames_iter:
        if frame.shape[:2] != (height, width):
            frame = cv2.resize(frame, (width, height)).astype(np.uint8)
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    writer.release()
    return output_path


async def frames_to_video_ffmpeg(
    frames: AsyncIterator[NDArray[np.uint8]] | Iterator[NDArray[np.uint8]],
    output_path: str | Path,
    fps: int = 30,
    width: int | None = None,
    height: int | None = None,
    codec: str = 'libx264',
    preset: str = 'medium',
    crf: int = 23,
    pix_fmt: str = 'yuv420p',
) -> Path:
    """Write frames to video using ffmpeg-python (better quality).

    Args:
        frames: Async or sync iterator of RGB frames
        output_path: Output video path
        fps: Frames per second
        width: Video width
        height: Video height
        codec: Video codec (libx264, libx265, libvpx-vp9, etc.)
        preset: Encoding preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
        crf: Constant Rate Factor (0-51, lower = better quality)
        pix_fmt: Pixel format (yuv420p for compatibility)

    Returns:
        Path to output video
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get first frame for dimensions
    if isinstance(frames, AsyncIterator):
        first_frame = await frames.__anext__()
    else:
        first_frame = next(iter(frames))

    if width is None:
        width = first_frame.shape[1]
    if height is None:
        height = first_frame.shape[0]

    # Use ffmpeg pipe input
    process = (
        ffmpeg.input('pipe:', format='rawvideo', pix_fmt='rgb24', s=f'{width}x{height}', r=fps)
        .output(
            str(output_path),
            vcodec=codec,
            preset=preset,
            crf=crf,
            pix_fmt=pix_fmt,
            r=fps,
        )
        .overwrite_output()
        .run_async(pipe_stdin=True, quiet=True)
    )

    # Write first frame
    process.stdin.write(first_frame.tobytes())

    # Write remaining frames
    async def write_frames() -> None:
        if isinstance(frames, AsyncIterator):
            async for frame in frames:
                if frame.shape[:2] != (height, width):
                    frame = cv2.resize(frame, (width, height)).astype(np.uint8)
                process.stdin.write(frame.tobytes())
        else:
            for frame in frames:
                if frame.shape[:2] != (height, width):
                    frame = cv2.resize(frame, (width, height)).astype(np.uint8)
                process.stdin.write(frame.tobytes())

    await write_frames()

    process.stdin.close()
    process.wait()

    return output_path


def extract_first_frame(video_path: str | Path) -> NDArray[np.uint8] | None:
    """Extract first frame from video as RGB array."""
    cap = cv2.VideoCapture(str(video_path))
    ret, frame = cap.read()
    cap.release()

    if ret:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.uint8)
    return None


def get_video_info(video_path: str | Path) -> dict:
    """Get video metadata."""
    cap = cv2.VideoCapture(str(video_path))
    info = {
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'duration': 0,
    }
    if info['fps'] > 0:
        info['duration'] = info['frame_count'] / info['fps']
    cap.release()
    return info


def create_thumbnail(
    video_path: str | Path,
    output_path: str | Path,
    timestamp: float = 0.0,
    size: tuple[int, int] | None = None,
) -> Path:
    """Create thumbnail from video at timestamp."""
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = int(timestamp * fps) if fps > 0 else 0

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError(f'Could not extract frame at {timestamp}s')

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    if size:
        frame_rgb = cv2.resize(frame_rgb, size)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    from PIL import Image

    Image.fromarray(frame_rgb).save(output_path, 'JPEG', quality=90)

    return output_path
