"""FluxWall utilities package."""

from fluxwall.utils.colors import (
    PALETTES,
    apply_colormap,
    create_gradient_palette,
    get_colormap,
    get_palette,
    hex_to_rgb,
    rgb_to_hex,
    save_colormap_preview,
)
from fluxwall.utils.math import (
    _fbm_2d,
    _gol_step,
    _julia_kernel,
    _mandelbrot_kernel,
    load_rle_pattern,
    parse_rule_string,
)
from fluxwall.utils.video import (
    create_thumbnail,
    extract_first_frame,
    frames_to_video,
    frames_to_video_ffmpeg,
    get_video_info,
)

__all__ = [
    'apply_colormap',
    'get_colormap',
    'get_palette',
    'hex_to_rgb',
    'rgb_to_hex',
    'create_gradient_palette',
    'save_colormap_preview',
    'PALETTES',
    '_gol_step',
    '_mandelbrot_kernel',
    '_julia_kernel',
    '_fbm_2d',
    'load_rle_pattern',
    'parse_rule_string',
    'frames_to_video',
    'frames_to_video_ffmpeg',
    'extract_first_frame',
    'get_video_info',
    'create_thumbnail',
]
