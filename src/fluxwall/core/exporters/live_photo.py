"""Live Photo export - HEIC still + MOV motion + manifest."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from fluxwall.core.exporters.heic import HEIF_AVAILABLE, save_heic
from fluxwall.core.exporters.video import export_mov


@dataclass
class LivePhotoManifest:
    """Manifest for Live Photo bundle."""

    version: str = '1.0'
    still_image: str = 'still.heic'
    motion_video: str = 'motion.mov'
    still_identifier: str = ''
    motion_identifier: str = ''
    duration: float = 3.0
    render_type: str = 'live_photo'
    width: int = 1290
    height: int = 2796

    def __post_init__(self) -> None:
        if not self.still_identifier:
            self.still_identifier = str(uuid.uuid4()).upper()
        if not self.motion_identifier:
            self.motion_identifier = str(uuid.uuid4()).upper()


class LivePhotoExporter:
    """Export generator frames as iOS Live Photo bundle."""

    def __init__(
        self,
        output_dir: str | Path,
        base_name: str = 'livephoto',
        duration: float = 3.0,
        fps: int = 30,
        width: int = 1290,
        height: int = 2796,
        quality: int = 90,
    ):
        self.output_dir = Path(output_dir)
        self.base_name = base_name
        self.duration = duration
        self.fps = fps
        self.width = width
        self.height = height
        self.quality = quality

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.still_path = self.output_dir / f'{base_name}_still.heic'
        self.motion_path = self.output_dir / f'{base_name}_motion.mov'
        self.manifest_path = self.output_dir / f'{base_name}_manifest.json'

    def export(
        self,
        frames: list[NDArray[np.uint8]] | Iterator[NDArray[np.uint8]],
        first_frame_idx: int = 0,
    ) -> dict[str, Path]:
        """Export frames as Live Photo bundle.

        Args:
            frames: List or iterator of RGB frames
            first_frame_idx: Index of frame to use as still image

        Returns:
            Dict with paths to still, motion, and manifest
        """
        frames_list = list(frames)
        total_frames = len(frames_list)

        if total_frames == 0:
            raise ValueError('No frames provided')

        # Ensure first_frame_idx is valid
        first_frame_idx = min(first_frame_idx, total_frames - 1)
        still_frame = frames_list[first_frame_idx]

        # Export still image (HEIC)
        if HEIF_AVAILABLE:
            still_path = save_heic(
                still_frame,
                self.still_path,
                quality=self.quality,
            )
        else:
            # Fallback to JPEG if HEIC not available
            from PIL import Image

            still_path = self.output_dir / f'{self.base_name}_still.jpg'
            Image.fromarray(still_frame).save(still_path, 'JPEG', quality=self.quality)

        # Export motion video (MOV) - use all frames or subset for duration
        target_frames = int(self.fps * self.duration)
        if total_frames > target_frames:
            # Sample frames evenly
            indices = np.linspace(0, total_frames - 1, target_frames, dtype=int)
            motion_frames = [frames_list[i] for i in indices]
        else:
            motion_frames = frames_list

        motion_path = export_mov(
            iter(motion_frames),
            self.motion_path,
            fps=self.fps,
            codec='libx264',
            preset='medium',
            crf=20,
            pixel_format='yuv420p',
        )

        # Create manifest
        manifest = LivePhotoManifest(
            still_image=still_path.name,
            motion_video=motion_path.name,
            duration=self.duration,
            width=self.width,
            height=self.height,
        )

        with self.manifest_path.open('w') as f:
            json.dump(asdict(manifest), f, indent=2)

        return {
            'still': still_path,
            'motion': motion_path,
            'manifest': self.manifest_path,
        }

    def export_from_generator(
        self,
        frame_generator: Iterator[NDArray[np.uint8]],
        total_frames: int,
        first_frame_idx: int = 0,
    ) -> dict[str, Path]:
        """Export from a frame generator without storing all frames in memory.

        Args:
            frame_generator: Generator yielding frames
            total_frames: Total number of frames to generate
            first_frame_idx: Frame index for still image

        Returns:
            Dict with paths
        """
        # Collect frames (for MVP, we collect; could stream to ffmpeg in future)
        frames = []
        for i, frame in enumerate(frame_generator):
            if i >= total_frames:
                break
            frames.append(frame)

        return self.export(frames, first_frame_idx)

    @staticmethod
    def create_ios_import_package(
        bundle_dir: str | Path,
        output_zip: str | Path | None = None,
    ) -> Path:
        """Create a ZIP package suitable for iOS import via Files app or Shortcuts.

        Note: iOS Photos doesn't natively import Live Photos from ZIP.
        This creates the file structure; users should use livephoto.online
        or an iOS Shortcut to combine into a real Live Photo.
        """
        import zipfile

        bundle_dir = Path(bundle_dir)
        output_zip = bundle_dir.with_suffix('.livephoto.zip') if output_zip is None else Path(output_zip)

        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in bundle_dir.iterdir():
                if file_path.is_file():
                    zf.write(file_path, file_path.name)

        return output_zip


def export_live_photo_bundle(
    frames: list[NDArray[np.uint8]],
    output_dir: str | Path,
    base_name: str = 'livephoto',
    duration: float = 3.0,
    fps: int = 30,
    width: int = 1290,
    height: int = 2796,
    quality: int = 90,
) -> dict[str, Path]:
    """Convenience function to export a Live Photo bundle."""
    exporter = LivePhotoExporter(
        output_dir=output_dir,
        base_name=base_name,
        duration=duration,
        fps=fps,
        width=width,
        height=height,
        quality=quality,
    )
    return exporter.export(frames)
