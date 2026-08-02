"""HEIC export using pillow-heif."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PIL import Image

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False


def save_heic(
    frame: NDArray[np.uint8],
    output_path: str | Path,
    quality: int = 90,
    compression: str = 'hevc',  # hevc or avc
    bit_depth: int = 8,
) -> Path:
    """Save a single RGB frame as HEIC image.

    Args:
        frame: RGB array (H, W, 3)
        output_path: Output file path
        quality: Quality (1-100)
        compression: Codec ('hevc' for HEVC, 'avc' for H.264/AVC)
        bit_depth: Bit depth (8, 10, 12)

    Returns:
        Path to saved file
    """
    if not HEIF_AVAILABLE:
        raise RuntimeError('pillow-heif not available. Install with: uv add pillow-heif')

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() not in ('.heic', '.heif'):
        output_path = output_path.with_suffix('.heic')

    # Convert numpy array to PIL Image
    if frame.dtype != np.uint8:
        frame = (frame * 255).astype(np.uint8)

    pil_image = Image.fromarray(frame, 'RGB')

    # Save as HEIC
    pil_image.save(
        output_path,
        format='HEIF',
        quality=quality,
        compression=compression,
        bit_depth=bit_depth,
    )

    return output_path


def load_heic(input_path: str | Path) -> NDArray[np.uint8]:
    """Load HEIC image as RGB numpy array."""
    if not HEIF_AVAILABLE:
        raise RuntimeError('pillow-heif not available')

    input_path = Path(input_path)
    image = Image.open(input_path)
    return np.array(image.convert('RGB'))


def heic_to_jpeg(
    input_path: str | Path,
    output_path: str | Path,
    quality: int = 95,
) -> Path:
    """Convert HEIC to JPEG."""
    if not HEIF_AVAILABLE:
        raise RuntimeError('pillow-heif not available')

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.open(input_path)
    image.save(output_path, 'JPEG', quality=quality, optimize=True)

    return output_path


def heic_to_png(input_path: str | Path, output_path: str | Path) -> Path:
    """Convert HEIC to PNG (lossless)."""
    if not HEIF_AVAILABLE:
        raise RuntimeError('pillow-heif not available')

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.open(input_path)
    image.save(output_path, 'PNG', optimize=True)

    return output_path


def get_heic_info(input_path: str | Path) -> dict:
    """Get metadata from HEIC file."""
    if not HEIF_AVAILABLE:
        raise RuntimeError('pillow-heif not available')

    input_path = Path(input_path)
    heif_file = pillow_heif.read_heif(input_path)

    return {
        'width': heif_file.width,
        'height': heif_file.height,
        'mode': heif_file.mode,
        'bit_depth': heif_file.bit_depth,
        'has_alpha': heif_file.has_alpha,
        'num_images': len(heif_file),
        'metadata': heif_file.metadata,
    }


def extract_heic_thumbnail(
    input_path: str | Path,
    output_path: str | Path,
    max_size: tuple[int, int] = (256, 256),
) -> Path:
    """Extract thumbnail from HEIC (first image if multi-image)."""
    if not HEIF_AVAILABLE:
        raise RuntimeError('pillow-heif not available')

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.open(input_path)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    image.save(output_path, 'JPEG', quality=85)

    return output_path
