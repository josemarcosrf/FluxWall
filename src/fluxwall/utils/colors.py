"""Color utilities: colormaps, palettes, color conversion."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.colors as mcolors
import numpy as np
from numpy.typing import NDArray

# Custom colormaps for specific effects
FIRE_COLORMAP = mcolors.LinearSegmentedColormap.from_list(
    'fire',
    [
        (0.00, (0.00, 0.00, 0.00)),  # Black
        (0.15, (0.50, 0.00, 0.00)),  # Dark red
        (0.30, (1.00, 0.00, 0.00)),  # Red
        (0.45, (1.00, 0.50, 0.00)),  # Orange
        (0.60, (1.00, 1.00, 0.00)),  # Yellow
        (0.75, (1.00, 1.00, 0.50)),  # Light yellow
        (1.00, (1.00, 1.00, 1.00)),  # White
    ],
    N=256,
)

PLASMA_CYCLE = mcolors.LinearSegmentedColormap.from_list(
    'plasma_cycle',
    [
        (0.0, (0.05, 0.03, 0.53)),
        (0.2, (0.47, 0.08, 0.66)),
        (0.4, (0.82, 0.29, 0.46)),
        (0.6, (0.97, 0.62, 0.18)),
        (0.8, (0.99, 0.91, 0.28)),
        (1.0, (0.05, 0.03, 0.53)),  # Loop back
    ],
    N=256,
)

AURORA_COLORMAP = mcolors.LinearSegmentedColormap.from_list(
    'aurora',
    [
        (0.00, (0.00, 0.05, 0.15)),  # Dark night
        (0.20, (0.00, 0.20, 0.40)),  # Deep blue
        (0.40, (0.00, 0.50, 0.30)),  # Teal
        (0.60, (0.20, 0.80, 0.20)),  # Green
        (0.80, (0.60, 0.90, 0.40)),  # Light green
        (1.00, (0.90, 1.00, 0.70)),  # Pale yellow-green
    ],
    N=256,
)

# Register custom colormaps
mpl.colormaps.register(FIRE_COLORMAP)
mpl.colormaps.register(PLASMA_CYCLE)
mpl.colormaps.register(AURORA_COLORMAP)


def get_colormap(name: str) -> mcolors.Colormap:
    """Get matplotlib colormap by name, with fallbacks."""
    name = name.lower().replace('-', '_')

    # Check custom colormaps
    custom_maps = {
        'fire': FIRE_COLORMAP,
        'plasma_cycle': PLASMA_CYCLE,
        'aurora': AURORA_COLORMAP,
    }
    if name in custom_maps:
        return custom_maps[name]

    # Try matplotlib
    try:
        return mpl.colormaps[name]
    except KeyError:
        return mpl.colormaps['viridis']


def apply_colormap(
    data: NDArray[np.floating],
    colormap: str = 'viridis',
    vmin: float = 0.0,
    vmax: float = 1.0,
    bytes_output: bool = True,
) -> NDArray[np.uint8]:
    """Apply colormap to normalized data array.

    Args:
        data: 2D array of values in [vmin, vmax] range
        colormap: Name of colormap
        vmin: Minimum data value
        vmax: Maximum data value
        bytes_output: Return uint8 (0-255) if True, else float (0-1)

    Returns:
        RGB array of shape (H, W, 3)
    """
    cmap = get_colormap(colormap)

    # Normalize
    normalized = np.clip((data - vmin) / (vmax - vmin), 0, 1)

    # Apply colormap (returns RGBA)
    rgba = np.asarray(cmap(normalized))

    # Extract RGB
    rgb = np.asarray(rgba[..., :3])

    if bytes_output:
        return (rgb * 255).astype(np.uint8)
    return rgb.astype(np.uint8)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB tuple to hex color string."""
    return f'#{r:02x}{g:02x}{b:02x}'


def interpolate_colors(
    color1: tuple[int, int, int],
    color2: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Linear interpolation between two RGB colors."""
    return (
        int(color1[0] + (color2[0] - color1[0]) * t),
        int(color1[1] + (color2[1] - color1[1]) * t),
        int(color1[2] + (color2[2] - color1[2]) * t),
    )


def create_gradient_palette(
    colors: list[tuple[int, int, int]],
    steps: int = 256,
) -> NDArray[np.uint8]:
    """Create a color palette by interpolating between colors."""
    if len(colors) < 2:
        raise ValueError('Need at least 2 colors')

    palette = np.zeros((steps, 3), dtype=np.uint8)
    segments = len(colors) - 1
    segment_steps = steps // segments

    for i in range(segments):
        c1 = colors[i]
        c2 = colors[i + 1]
        start = i * segment_steps
        end = start + segment_steps if i < segments - 1 else steps

        for j, idx in enumerate(range(start, end)):
            t = j / (end - start)
            palette[idx] = interpolate_colors(c1, c2, t)

    return palette


# Preset palettes
PALETTES = {
    'game_of_life': create_gradient_palette(
        [
            (0, 0, 0),  # Dead
            (20, 20, 60),  # Trail start
            (100, 50, 150),  # Trail mid
            (255, 100, 50),  # Trail bright
            (255, 255, 255),  # Live
        ]
    ),
    'fire': create_gradient_palette(
        [
            (0, 0, 0),
            (64, 0, 0),
            (192, 0, 0),
            (255, 128, 0),
            (255, 255, 0),
            (255, 255, 255),
        ]
    ),
    'ocean': create_gradient_palette(
        [
            (0, 5, 30),
            (0, 30, 80),
            (0, 100, 150),
            (50, 180, 200),
            (150, 220, 255),
        ]
    ),
    'forest': create_gradient_palette(
        [
            (5, 20, 5),
            (20, 80, 20),
            (60, 150, 40),
            (120, 200, 80),
            (180, 230, 140),
        ]
    ),
    'sunset': create_gradient_palette(
        [
            (20, 0, 40),
            (80, 20, 60),
            (180, 60, 40),
            (255, 140, 30),
            (255, 220, 100),
        ]
    ),
}


def get_palette(name: str) -> NDArray[np.uint8]:
    """Get a preset palette by name."""
    return PALETTES.get(name, PALETTES['game_of_life'])


def save_colormap_preview(
    colormap: str,
    output_path: str | Path,
    width: int = 512,
    height: int = 64,
) -> Path:
    """Save a visual preview of a colormap."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gradient = np.linspace(0, 1, width).reshape(1, -1)
    gradient = np.repeat(gradient, height, axis=0)

    rgb = apply_colormap(gradient, colormap, bytes_output=True)

    from PIL import Image

    Image.fromarray(rgb, 'RGB').save(output_path)

    return output_path
