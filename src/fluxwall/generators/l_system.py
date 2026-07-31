"""L-System Generator (scaffolded for future implementation)."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from fluxwall.core.models import LSystemParams
from fluxwall.generators.base import Generator, GeneratorParams
from fluxwall.generators.registry import register_generator
from fluxwall.utils.colors import apply_colormap


@register_generator
class LSystemGenerator(Generator):
    """L-System fractal plant generator (scaffolded)."""

    name: str = 'l_system'
    display_name: str = 'L-System'
    description: str = 'Lindenmayer system fractal plants and trees'

    param_schema: dict = {
        'type': 'object',
        'properties': {
            'width': {'type': 'integer', 'minimum': 100, 'maximum': 3000, 'default': 1170},
            'height': {'type': 'integer', 'minimum': 100, 'maximum': 5000, 'default': 2532},
            'fps': {'type': 'integer', 'minimum': 1, 'maximum': 60, 'default': 30},
            'duration_sec': {'type': 'number', 'minimum': 0.5, 'maximum': 30.0, 'default': 4.0},
            'colormap': {'type': 'string', 'default': 'viridis'},
            'seed': {'type': ['integer', 'null'], 'default': None},
            'axiom': {'type': 'string', 'default': 'X'},
            'rules': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {'X': 'F+[[X]-X]-F[-FX]+X', 'F': 'FF'},
            },
            'angle': {'type': 'number', 'minimum': 1.0, 'maximum': 180.0, 'default': 25.0},
            'iterations': {'type': 'integer', 'minimum': 1, 'maximum': 10, 'default': 6},
            'line_width': {'type': 'number', 'minimum': 0.5, 'maximum': 10.0, 'default': 2.0},
            'color_by_depth': {'type': 'boolean', 'default': True},
            'color_scheme': {'type': 'string', 'enum': ['plant', 'rainbow', 'fire', 'mono'], 'default': 'plant'},
            'animation_mode': {'type': 'string', 'enum': ['grow', 'rotate', 'wind'], 'default': 'grow'},
            'wind_strength': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0, 'default': 0.0},
        },
        'required': ['width', 'height', 'fps', 'duration_sec'],
    }

    presets = {
        'fractal_tree': {
            'name': 'Fractal Tree',
            'description': 'Classic binary tree fractal',
            'params': {'axiom': 'F', 'rules': {'F': 'FF+[+F-F-F]-[-F+F+F]'}, 'angle': 22.5, 'iterations': 5},
        },
        'barnsley_fern': {
            'name': 'Barnsley Fern',
            'description': 'Iconic fern fractal',
            'params': {'axiom': 'X', 'rules': {'X': 'F+[[X]-X]-F[-FX]+X', 'F': 'FF'}, 'angle': 25, 'iterations': 6},
        },
        'dragon_curve': {
            'name': 'Dragon Curve',
            'description': 'Heighway dragon curve',
            'params': {'axiom': 'FX', 'rules': {'X': 'X+YF+', 'Y': '-FX-Y'}, 'angle': 90, 'iterations': 12},
        },
        'koch_snowflake': {
            'name': 'Koch Snowflake',
            'description': 'Classic Koch snowflake',
            'params': {'axiom': 'F--F--F', 'rules': {'F': 'F+F--F+F'}, 'angle': 60, 'iterations': 5},
        },
        'plant': {
            'name': 'Fractal Plant',
            'description': 'Organic plant-like structure',
            'params': {'axiom': 'X', 'rules': {'X': 'F+[[X]-X]-F[-FX]+X', 'F': 'FF'}, 'angle': 25, 'iterations': 6},
        },
    }

    def generate_frame(self, frame_idx: int, params: GeneratorParams) -> NDArray[np.uint8]:
        # Placeholder - returns gradient for now
        h, w = params.height, params.width
        y_grad = np.linspace(0, 1, h).reshape(-1, 1)
        x_grad = np.linspace(0, 1, w).reshape(1, -1)
        gradient = (y_grad + x_grad) / 2
        return apply_colormap(gradient, getattr(params, 'colormap', 'viridis'))

    def validate_params(self, params: dict[str, Any]) -> GeneratorParams:
        return LSystemParams(**params)
