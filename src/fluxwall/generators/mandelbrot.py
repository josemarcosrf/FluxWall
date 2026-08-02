"""Mandelbrot Set generator with zoom animation."""

from __future__ import annotations

from typing import Any

import numpy as np
from numba import njit, prange
from numpy.typing import NDArray

from fluxwall.core.models import MandelbrotParams
from fluxwall.generators.base import Generator, GeneratorParams
from fluxwall.generators.registry import register_generator
from fluxwall.utils.colors import apply_colormap


@njit(parallel=True, cache=True)
def _mandelbrot_kernel(
    re: NDArray[np.float64],
    im: NDArray[np.float64],
    max_iter: int,
    smooth: bool,
) -> NDArray[np.float64]:
    """Compute Mandelbrot iterations for each point in parallel."""
    h, w = len(im), len(re)
    result = np.zeros((h, w), dtype=np.float64)

    for i in prange(h):  # type: ignore[attr-defined]
        cy = im[i]
        for j in range(w):
            cx = re[j]
            x = 0.0
            y = 0.0
            iter_count = 0

            for _ in range(max_iter):
                x2 = x * x
                y2 = y * y
                if x2 + y2 > 4.0:
                    break
                y = 2.0 * x * y + cy
                x = x2 - y2 + cx
                iter_count += 1

            if smooth and iter_count < max_iter:
                # Smooth coloring using fractional iteration
                zn = x * x + y * y
                if zn > 0:
                    mu = iter_count + 1 - np.log(np.log(zn)) / np.log(2)
                    result[i, j] = mu
                else:
                    result[i, j] = iter_count
            else:
                result[i, j] = iter_count

    return result


@register_generator
class MandelbrotGenerator(Generator):
    """Mandelbrot Set with exponential zoom animation."""

    name = 'mandelbrot'
    display_name = 'Mandelbrot Set'
    description = 'Classic Mandelbrot fractal with smooth zoom and color cycling'

    param_schema = {
        'type': 'object',
        'properties': {
            'width': {'type': 'integer', 'minimum': 100, 'maximum': 2000, 'default': 1170},
            'height': {'type': 'integer', 'minimum': 100, 'maximum': 4000, 'default': 2532},
            'fps': {'type': 'integer', 'minimum': 1, 'maximum': 60, 'default': 30},
            'duration_sec': {'type': 'number', 'minimum': 0.5, 'maximum': 30, 'default': 4.0},
            'colormap': {'type': 'string', 'default': 'magma'},
            'seed': {'type': ['integer', 'null'], 'default': None},
            'center_x': {'type': 'number', 'default': -0.5},
            'center_y': {'type': 'number', 'default': 0.0},
            'zoom': {'type': 'number', 'minimum': 0.1, 'maximum': 1e12, 'default': 1.0},
            'max_iter': {'type': 'integer', 'minimum': 50, 'maximum': 10000, 'default': 500},
            'zoom_factor_per_frame': {'type': 'number', 'minimum': 1.0, 'maximum': 1.5, 'default': 1.02},
            'color_cycle_speed': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0, 'default': 0.05},
            'smooth_coloring': {'type': 'boolean', 'default': True},
        },
        'required': ['width', 'height', 'fps', 'duration_sec'],
    }

    presets = {
        'classic': {
            'name': 'Classic View',
            'description': 'Full Mandelbrot set at default zoom',
            'params': {
                'center_x': -0.5,
                'center_y': 0.0,
                'zoom': 1.0,
                'max_iter': 300,
                'zoom_factor_per_frame': 1.0,
            },
        },
        'seahorse_valley': {
            'name': 'Seahorse Valley',
            'description': 'Deep zoom into the iconic seahorse valley',
            'params': {
                'center_x': -0.7436438870371587,
                'center_y': 0.13182590420531197,
                'zoom': 1e6,
                'max_iter': 2000,
                'zoom_factor_per_frame': 1.03,
            },
        },
        'elephant_valley': {
            'name': 'Elephant Valley',
            'description': 'Zoom into the elephant valley region',
            'params': {
                'center_x': 0.2845,
                'center_y': 0.012,
                'zoom': 1e5,
                'max_iter': 1500,
                'zoom_factor_per_frame': 1.025,
            },
        },
        'triple_spiral': {
            'name': 'Triple Spiral',
            'description': 'Three-armed spiral zoom',
            'params': {
                'center_x': -0.1011,
                'center_y': 0.9563,
                'zoom': 1e4,
                'max_iter': 1000,
                'zoom_factor_per_frame': 1.02,
            },
        },
        'minibrot': {
            'name': 'Mini Mandelbrot',
            'description': 'Zoom into a miniature copy of the whole set',
            'params': {
                'center_x': -1.749,
                'center_y': 0.0,
                'zoom': 1e7,
                'max_iter': 3000,
                'zoom_factor_per_frame': 1.04,
            },
        },
    }

    def generate_frame(self, frame_idx: int, params: GeneratorParams) -> NDArray[np.uint8]:
        # Parse parameters
        center_x = getattr(params, 'center_x', -0.5)
        center_y = getattr(params, 'center_y', 0.0)
        base_zoom = getattr(params, 'zoom', 1.0)
        max_iter = getattr(params, 'max_iter', 500)
        zoom_factor = getattr(params, 'zoom_factor_per_frame', 1.02)
        color_cycle = getattr(params, 'color_cycle_speed', 0.05)
        smooth = getattr(params, 'smooth_coloring', True)
        colormap = getattr(params, 'colormap', 'magma')

        # Calculate zoom for this frame (exponential)
        zoom = base_zoom * (zoom_factor**frame_idx)

        # Calculate view bounds
        aspect = params.width / params.height
        re_range = 3.0 / zoom
        im_range = re_range / aspect

        re_min = center_x - re_range / 2
        re_max = center_x + re_range / 2
        im_min = center_y - im_range / 2
        im_max = center_y + im_range / 2

        # Create coordinate arrays
        re = np.linspace(re_min, re_max, params.width, dtype=np.float64)
        im = np.linspace(im_max, im_min, params.height, dtype=np.float64)  # Flip Y

        # Compute Mandelbrot iterations
        iterations = _mandelbrot_kernel(re, im, max_iter, smooth)

        # Normalize against the actual observed iteration range rather than max_iter,
        # since escaping points rarely get anywhere near max_iter — dividing by the
        # raw max_iter compresses almost everything near 0 and washes out the colors.
        iter_max = iterations.max()
        normalized = np.log1p(iterations) / np.log1p(iter_max) if iter_max > 0 else iterations

        # Apply color cycling by shifting the normalized values
        if color_cycle > 0:
            cycle_shift = (frame_idx * color_cycle) % 1.0
            normalized = (normalized + cycle_shift) % 1.0

        # Apply colormap
        return apply_colormap(normalized, colormap)

    def validate_params(self, params: dict[str, Any]) -> GeneratorParams:
        return MandelbrotParams(**params)
