"""Julia Set Generator with spin/zoom animations."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from fluxwall.core.models import JuliaParams
from fluxwall.generators.base import Generator, GeneratorParams
from fluxwall.generators.registry import register_generator
from fluxwall.utils.colors import apply_colormap
from fluxwall.utils.math import _julia_kernel


@register_generator
class JuliaGenerator(Generator):
    """Julia Set fractal generator with spin and zoom animations."""

    name: str = 'julia'
    display_name: str = 'Julia Set'
    description: str = 'Julia set fractal with rotation and zoom animations'

    param_schema: dict = {
        'type': 'object',
        'properties': {
            'width': {'type': 'integer', 'minimum': 100, 'maximum': 3000, 'default': 1170},
            'height': {'type': 'integer', 'minimum': 100, 'maximum': 5000, 'default': 2532},
            'fps': {'type': 'integer', 'minimum': 1, 'maximum': 60, 'default': 30},
            'duration_sec': {'type': 'number', 'minimum': 0.5, 'maximum': 30.0, 'default': 4.0},
            'colormap': {'type': 'string', 'default': 'magma'},
            'seed': {'type': ['integer', 'null'], 'default': None},
            'c_real': {'type': 'number', 'minimum': -2.0, 'maximum': 2.0, 'default': -0.7},
            'c_imag': {'type': 'number', 'minimum': -2.0, 'maximum': 2.0, 'default': 0.27015},
            'zoom': {'type': 'number', 'minimum': 0.1, 'maximum': 1e10, 'default': 1.0},
            'max_iter': {'type': 'integer', 'minimum': 50, 'maximum': 10000, 'default': 300},
            'animation_mode': {'type': 'string', 'enum': ['spin', 'zoom', 'spin_zoom'], 'default': 'spin'},
            'spin_radius': {'type': 'number', 'minimum': 0.1, 'maximum': 2.0, 'default': 0.7885},
            'spin_speed': {'type': 'number', 'minimum': 0.0, 'maximum': 2.0, 'default': 1.0},
            'zoom_factor_per_frame': {'type': 'number', 'minimum': 1.0, 'maximum': 1.5, 'default': 1.02},
            'color_cycle_speed': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0, 'default': 0.03},
            'smooth_coloring': {'type': 'boolean', 'default': True},
        },
        'required': ['width', 'height', 'fps', 'duration_sec'],
    }

    presets = {
        'douady_rabbit': {
            'name': 'Douady Rabbit',
            'description': 'Classic rabbit-shaped Julia set',
            'params': {'c_real': -0.123, 'c_imag': 0.745, 'zoom': 1.2, 'max_iter': 300, 'animation_mode': 'spin'},
        },
        'dendrite': {
            'name': 'Dendrite',
            'description': 'Tree-like branching Julia set',
            'params': {'c_real': 0.0, 'c_imag': -1.0, 'zoom': 1.5, 'max_iter': 300, 'animation_mode': 'spin'},
        },
        'spiral': {
            'name': 'Spiral',
            'description': 'Elegant spiral pattern',
            'params': {'c_real': -0.7, 'c_imag': 0.27015, 'zoom': 1.0, 'max_iter': 300, 'animation_mode': 'spin_zoom'},
        },
        'cauliflower': {
            'name': 'Cauliflower',
            'description': 'Cauliflower-like Julia set',
            'params': {'c_real': -0.12, 'c_imag': -0.77, 'zoom': 1.0, 'max_iter': 300, 'animation_mode': 'spin'},
        },
        'lightning': {
            'name': 'Lightning',
            'description': 'Lightning bolt patterns',
            'params': {'c_real': 0.3, 'c_imag': 0.5, 'zoom': 1.5, 'max_iter': 400, 'animation_mode': 'spin_zoom'},
        },
        'basilica': {
            'name': 'Basilica',
            'description': 'Basilica-shaped main cardioid',
            'params': {'c_real': -0.75, 'c_imag': 0.0, 'zoom': 1.2, 'max_iter': 300, 'animation_mode': 'spin'},
        },
        'siegel_disk': {
            'name': 'Siegel Disk',
            'description': 'Siegel disk with irrational rotation',
            'params': {'c_real': -0.3905, 'c_imag': 0.5867, 'zoom': 1.0, 'max_iter': 300, 'animation_mode': 'spin'},
        },
    }

    def generate_frame(self, frame_idx: int, params: GeneratorParams) -> NDArray[np.uint8]:
        # Parse parameters
        c_real = getattr(params, 'c_real', -0.7)
        c_imag = getattr(params, 'c_imag', 0.27015)
        base_zoom = getattr(params, 'zoom', 1.0)
        max_iter = getattr(params, 'max_iter', 300)
        anim_mode = getattr(params, 'animation_mode', 'spin')
        spin_radius = getattr(params, 'spin_radius', 0.7885)
        spin_speed = getattr(params, 'spin_speed', 1.0)
        zoom_factor = getattr(params, 'zoom_factor_per_frame', 1.02)
        color_cycle = getattr(params, 'color_cycle_speed', 0.03)
        smooth = getattr(params, 'smooth_coloring', True)
        colormap = getattr(params, 'colormap', 'magma')

        total_frames = int(params.fps * params.duration_sec)

        # Calculate c parameter based on animation mode
        if anim_mode in ('spin', 'spin_zoom'):
            # Orbit c around the origin at the preset's own radius/angle (scaled by
            # spin_radius relative to its schema default), so each preset keeps its
            # distinct shape instead of collapsing to a shared default circle.
            base_r = np.hypot(c_real, c_imag) * (spin_radius / 0.7885)
            base_theta = np.arctan2(c_imag, c_real)
            theta = base_theta + (2 * np.pi * frame_idx * spin_speed) / total_frames
            c_real = base_r * np.cos(theta)
            c_imag = base_r * np.sin(theta)

        # Calculate zoom
        zoom = base_zoom * zoom_factor**frame_idx if anim_mode in ('zoom', 'spin_zoom') else base_zoom

        # Calculate view bounds
        aspect = params.width / params.height
        re_range = 3.0 / zoom
        im_range = re_range / aspect

        re_min = -re_range / 2
        re_max = re_range / 2
        im_min = -im_range / 2
        im_max = im_range / 2

        # Create coordinate arrays
        re = np.linspace(re_min, re_max, params.width, dtype=np.float64)
        im = np.linspace(im_max, im_min, params.height, dtype=np.float64)  # Flip Y

        # Compute Julia iterations
        iterations = _julia_kernel(re, im, c_real, c_imag, max_iter, smooth)

        # Normalize against the actual observed iteration range rather than max_iter,
        # since escaping points rarely get anywhere near max_iter — dividing by the
        # raw max_iter compresses almost everything near 0 and washes out the colors.
        iter_max = iterations.max()
        normalized = np.log1p(iterations) / np.log1p(iter_max) if iter_max > 0 else iterations

        # Apply color cycling
        if color_cycle > 0:
            cycle_shift = (frame_idx * color_cycle) % 1.0
            normalized = (normalized + cycle_shift) % 1.0

        # Apply colormap
        return apply_colormap(normalized, colormap)

    def validate_params(self, params: dict[str, Any]) -> GeneratorParams:
        return JuliaParams(**params)
