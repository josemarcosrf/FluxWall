"""Video export utilities using ffmpeg-python and OpenCV."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import cv2
import ffmpeg
import numpy as np
from numpy.typing import NDArray


def export_video(
    frames: Iterator[NDArray[np.uint8]],
    output_path: str | Path,
    fps: int = 30,
    width: int = 1170,
    height: int = 2532,
    codec: str = 'libx264',
    preset: str = 'medium',
    crf: int = 18,
    pixel_format: str = 'yuv420p',
) -> Path:
    """Export frames to MP4 video using ffmpeg.

    Args:
        frames: Iterator yielding RGB frames (H, W, 3)
        output_path: Output file path
        fps: Frames per second
        width: Frame width
        height: Frame height
        codec: Video codec (libx264, libx265, h264_videotoolbox, etc.)
        preset: Encoding preset (ultrafast to veryslow)
        crf: Constant Rate Factor (0-51, lower = better quality)
        pixel_format: Output pixel format

    Returns:
        Path to output file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # libx264 with yuv420p requires even dimensions. Round down so odd
    # resolutions (e.g. iPhone 15 Pro 1179x2556) encode without a broken pipe.
    even_w = width - (width % 2)
    even_h = height - (height % 2)

    # Build ffmpeg command
    process = (
        ffmpeg.input(
            'pipe:',
            format='rawvideo',
            pix_fmt='rgb24',
            s=f'{even_w}x{even_h}',
            framerate=fps,
        )
        .output(
            str(output_path),
            vcodec=codec,
            preset=preset,
            crf=crf,
            pix_fmt=pixel_format,
            r=fps,
            movflags='+faststart',  # For web streaming
        )
        .overwrite_output()
        .run_async(pipe_stdin=True)
    )

    try:
        for frame in frames:
            # Resize if shape doesn't match the (even) encode size
            if frame.shape[:2] != (even_h, even_w):
                frame = cv2.resize(frame, (even_w, even_h), interpolation=cv2.INTER_LINEAR).astype(np.uint8)
            # Write raw RGB data to stdin
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
        process.wait()

    return output_path


async def export_video_async(
    frames: Iterator[NDArray[np.uint8]],
    output_path: str | Path,
    fps: int = 30,
    width: int = 1170,
    height: int = 2532,
    codec: str = 'libx264',
    preset: str = 'medium',
    crf: int = 18,
    pixel_format: str = 'yuv420p',
    chunk_size: int = 100,
) -> Path:
    """Async version of export_video for non-blocking operation."""
    return await asyncio.get_event_loop().run_in_executor(
        None,
        export_video,
        frames,
        output_path,
        fps,
        width,
        height,
        codec,
        preset,
        crf,
        pixel_format,
    )


def export_mov(
    frames: Iterator[NDArray[np.uint8]],
    output_path: str | Path,
    fps: int = 30,
    width: int = 1170,
    height: int = 2532,
    codec: str = 'libx264',
    preset: str = 'medium',
    crf: int = 18,
    pixel_format: str = 'yuv420p',
) -> Path:
    """Export frames to MOV container (iOS compatible).

    Same as export_video but ensures MOV container and compatible settings.
    """
    output_path = Path(output_path)
    if output_path.suffix.lower() != '.mov':
        output_path = output_path.with_suffix('.mov')

    return export_video(
        frames,
        output_path,
        fps=fps,
        width=width,
        height=height,
        codec=codec,
        preset=preset,
        crf=crf,
        pixel_format=pixel_format,
    )


def export_video_opencv(
    frames: Iterator[NDArray[np.uint8]],
    output_path: str | Path,
    fps: int = 30,
    width: int = 1170,
    height: int = 2532,
    codec: str = 'mp4v',  # FourCC code
) -> Path:
    """Export video using OpenCV (fallback, lower quality).

    Note: OpenCV's mp4v codec produces files that may not play in all browsers.
    Use export_video() for better compatibility.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*codec)  # type: ignore[attr-defined]
    writer = cv2.VideoWriter(
        str(output_path),
        fourcc,
        fps,
        (width, height),
        isColor=True,
    )

    try:
        for frame in frames:
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR).astype(np.uint8)
            # OpenCV uses BGR
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            writer.write(bgr)
    finally:
        writer.release()

    return output_path


def get_video_duration(output_path: str | Path, fps: int) -> float:
    """Get video duration in seconds."""
    import subprocess

    result = subprocess.run(
        [
            'ffprobe',
            '-v',
            'error',
            '-select_streams',
            'v:0',
            '-show_entries',
            'stream=nb_frames',
            '-of',
            'csv=p=0',
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        frames = int(result.stdout.strip())
        return frames / fps
    return 0.0


def validate_video(output_path: str | Path) -> bool:
    """Check if video file is valid and playable."""
    import subprocess

    result = subprocess.run(['ffprobe', '-v', 'error', str(output_path)], capture_output=True)
    return result.returncode == 0
