"""Conway's Game of Life Generator with Numba JIT acceleration."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from fluxwall.core.models import GameOfLifeParams
from fluxwall.generators.base import Generator, GeneratorParams
from fluxwall.generators.registry import register_generator
from fluxwall.utils.colors import apply_colormap
from fluxwall.utils.math import _gol_step


@register_generator
class GameOfLifeGenerator(Generator):
    """Conway's Game of Life with trail-based color cycling."""

    name: str = 'game_of_life'
    display_name: str = 'Game of Life'
    description: str = "Conway's Game of Life with customizable rules and color trails"

    param_schema: dict = {
        'type': 'object',
        'properties': {
            'width': {'type': 'integer', 'minimum': 100, 'maximum': 3000, 'default': 1170},
            'height': {'type': 'integer', 'minimum': 100, 'maximum': 5000, 'default': 2532},
            'fps': {'type': 'integer', 'minimum': 1, 'maximum': 60, 'default': 30},
            'duration_sec': {'type': 'number', 'minimum': 0.5, 'maximum': 30.0, 'default': 4.0},
            'colormap': {'type': 'string', 'default': 'plasma'},
            'seed': {'type': ['integer', 'null'], 'default': None},
            'grid_width': {'type': 'integer', 'minimum': 50, 'maximum': 1000, 'default': 300},
            'grid_height': {'type': 'integer', 'minimum': 50, 'maximum': 1000, 'default': 650},
            'rule_birth': {'type': 'string', 'pattern': '^[0-8]+$', 'default': '3'},
            'rule_survive': {'type': 'string', 'pattern': '^[0-8]+$', 'default': '23'},
            'wrap_edges': {'type': 'boolean', 'default': True},
            'initial_pattern': {
                'type': 'string',
                'enum': [
                    'random',
                    'gosper_gun',
                    'glider',
                    'pulsar',
                    'pentadecathlon',
                    'acorn',
                    'r_pentomino',
                    'diehard',
                ],
                'default': 'random',
            },
            'pattern_scale': {'type': 'number', 'minimum': 0.5, 'maximum': 5.0, 'default': 1.0},
            'trail_length': {'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 30},
            'trail_decay': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0, 'default': 0.95},
            'color_live': {'type': 'string', 'format': 'color', 'default': '#FFFFFF'},
            'color_dead': {'type': 'string', 'format': 'color', 'default': '#000000'},
            'trail_colormap': {'type': 'string', 'default': 'plasma'},
        },
        'required': ['width', 'height', 'fps', 'duration_sec'],
    }

    presets = {
        'gosper_gun': {
            'name': 'Gosper Glider Gun',
            'description': 'The classic infinite glider generator',
            'params': {
                'initial_pattern': 'gosper_gun',
                'grid_width': 300,
                'grid_height': 650,
                'trail_length': 40,
                'trail_decay': 0.97,
            },
        },
        'glider_swarm': {
            'name': 'Glider Swarm',
            'description': 'Multiple gliders in random directions',
            'params': {
                'initial_pattern': 'glider',
                'grid_width': 400,
                'grid_height': 800,
                'trail_length': 25,
                'trail_decay': 0.93,
            },
        },
        'pulsar': {
            'name': 'Pulsar',
            'description': 'Period-3 oscillator',
            'params': {
                'initial_pattern': 'pulsar',
                'grid_width': 200,
                'grid_height': 400,
                'trail_length': 15,
                'trail_decay': 0.9,
            },
        },
        'pentadecathlon': {
            'name': 'Pentadecathlon',
            'description': 'Period-15 oscillator',
            'params': {
                'initial_pattern': 'pentadecathlon',
                'grid_width': 200,
                'grid_height': 400,
                'trail_length': 20,
                'trail_decay': 0.92,
            },
        },
        'acorn': {
            'name': 'Acorn',
            'description': 'Methuselah - runs for 5206 generations',
            'params': {
                'initial_pattern': 'acorn',
                'grid_width': 500,
                'grid_height': 1000,
                'trail_length': 50,
                'trail_decay': 0.98,
            },
        },
        'r_pentomino': {
            'name': 'R-Pentomino',
            'description': 'Classic chaotic pattern',
            'params': {
                'initial_pattern': 'r_pentomino',
                'grid_width': 300,
                'grid_height': 600,
                'trail_length': 30,
                'trail_decay': 0.95,
            },
        },
        'diehard': {
            'name': 'Diehard',
            'description': 'Disappears after 130 generations',
            'params': {
                'initial_pattern': 'diehard',
                'grid_width': 200,
                'grid_height': 400,
                'trail_length': 20,
                'trail_decay': 0.9,
            },
        },
        'random_soup': {
            'name': 'Random Soup',
            'description': 'Random initial state at 30% density',
            'params': {
                'initial_pattern': 'random',
                'grid_width': 400,
                'grid_height': 800,
                'trail_length': 30,
                'trail_decay': 0.95,
            },
        },
    }

    def __init__(self) -> None:
        super().__init__()
        from collections.abc import Callable

        self._patterns: dict[str, Callable[[np.ndarray, int, int, float], None]] = {
            'gosper_gun': self._pattern_gosper_gun,
            'glider': self._pattern_glider,
            'pulsar': self._pattern_pulsar,
            'pentadecathlon': self._pattern_pentadecathlon,
            'acorn': self._pattern_acorn,
            'r_pentomino': self._pattern_r_pentomino,
            'diehard': self._pattern_diehard,
        }

    def _create_grid(self, params: GeneratorParams) -> np.ndarray:
        """Create initial grid based on pattern."""
        gw = getattr(params, 'grid_width', 300)
        gh = getattr(params, 'grid_height', 650)
        grid = np.zeros((gh, gw), dtype=np.uint8)
        pattern = getattr(params, 'initial_pattern', 'random')

        if pattern == 'random':
            density = 0.3
            if hasattr(params, 'seed') and params.seed is not None:
                np.random.seed(params.seed)
            grid[np.random.random((gh, gw)) < density] = 1
        elif pattern in self._patterns:
            self._patterns[pattern](grid, gw, gh, getattr(params, 'pattern_scale', 1.0))

        return grid

    def _pattern_gosper_gun(self, grid: np.ndarray, gw: int, gh: int, scale: float) -> None:
        """Gosper Glider Gun pattern."""
        # Standard gun at offset
        ox, oy = gw // 4, gh // 2
        gun = [
            (0, 24),
            (1, 22),
            (1, 24),
            (2, 12),
            (2, 13),
            (2, 20),
            (2, 21),
            (2, 34),
            (2, 35),
            (3, 11),
            (3, 15),
            (3, 20),
            (3, 21),
            (3, 34),
            (3, 35),
            (4, 0),
            (4, 1),
            (4, 10),
            (4, 16),
            (4, 20),
            (4, 21),
            (5, 0),
            (5, 1),
            (5, 10),
            (5, 14),
            (5, 16),
            (5, 17),
            (5, 22),
            (5, 24),
            (6, 10),
            (6, 16),
            (6, 24),
            (7, 11),
            (7, 15),
            (8, 12),
            (8, 13),
        ]
        for dx, dy in gun:
            x, y = ox + int(dx * scale), oy + int(dy * scale)
            if 0 <= x < gh and 0 <= y < gw:
                grid[x, y] = 1

    def _pattern_glider(self, grid: np.ndarray, gw: int, gh: int, scale: float) -> None:
        """Place multiple gliders at random positions."""
        glider = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
        for _ in range(20):
            ox = np.random.randint(0, gh - 5)
            oy = np.random.randint(0, gw - 5)
            for dx, dy in glider:
                x, y = ox + int(dx * scale), oy + int(dy * scale)
                if 0 <= x < gh and 0 <= y < gw:
                    grid[x, y] = 1

    def _pattern_pulsar(self, grid: np.ndarray, gw: int, gh: int, scale: float) -> None:
        """Pulsar oscillator."""
        ox, oy = gh // 2 - 7, gw // 2 - 7
        # Pulsar pattern
        for dx in [0, 5, 7, 12]:
            for dy in [2, 3, 4, 8, 9, 10]:
                x, y = ox + dx, oy + dy
                if 0 <= x < gh and 0 <= y < gw:
                    grid[x, y] = 1
                    grid[y, x] = 1

    def _pattern_pentadecathlon(self, grid: np.ndarray, gw: int, gh: int, scale: float) -> None:
        """Pentadecathlon oscillator."""
        ox, oy = gh // 2 - 3, gw // 2 - 7
        pattern = [
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (0, 7),
            (0, 8),
            (1, 0),
            (1, 9),
            (2, 1),
            (2, 2),
            (2, 3),
            (2, 4),
            (2, 5),
            (2, 6),
            (2, 7),
            (2, 8),
        ]
        for dx, dy in pattern:
            x, y = ox + dx, oy + dy
            if 0 <= x < gh and 0 <= y < gw:
                grid[x, y] = 1

    def _pattern_acorn(self, grid: np.ndarray, gw: int, gh: int, scale: float) -> None:
        """Acorn methuselah."""
        ox, oy = gh // 2, gw // 2
        acorn = [(0, 1), (1, 3), (2, 0), (2, 1), (2, 4), (2, 5), (2, 6)]
        for dx, dy in acorn:
            x, y = ox + dx, oy + dy
            if 0 <= x < gh and 0 <= y < gw:
                grid[x, y] = 1

    def _pattern_r_pentomino(self, grid: np.ndarray, gw: int, gh: int, scale: float) -> None:
        """R-pentomino."""
        ox, oy = gh // 2, gw // 2
        r_pent = [(0, 1), (0, 2), (1, 0), (1, 1), (2, 1)]
        for dx, dy in r_pent:
            x, y = ox + dx, oy + dy
            if 0 <= x < gh and 0 <= y < gw:
                grid[x, y] = 1

    def _pattern_diehard(self, grid: np.ndarray, gw: int, gh: int, scale: float) -> None:
        """Diehard pattern."""
        ox, oy = gh // 2, gw // 2
        diehard = [(0, 6), (1, 0), (1, 1), (2, 1), (2, 5), (2, 6), (2, 7)]
        for dx, dy in diehard:
            x, y = ox + dx, oy + dy
            if 0 <= x < gh and 0 <= y < gw:
                grid[x, y] = 1

    def generate_frame(self, frame_idx: int, params: GeneratorParams) -> NDArray[np.uint8]:
        # We need to maintain state across frames - use a closure or class attr
        if frame_idx == 0:
            # Initialize on first frame
            grid = self._create_grid(params)
            trail = np.zeros_like(grid, dtype=np.float32)
            # Store as attributes for next frames
            self._current_grid = grid
            self._current_trail = trail
            self._params = params
        else:
            grid = self._current_grid
            trail = self._current_trail
            params = self._params

        # Game of Life step
        rule_birth = getattr(params, 'rule_birth', '3')
        rule_survive = getattr(params, 'rule_survive', '23')
        wrap = getattr(params, 'wrap_edges', True)

        birth_set = {int(c) for c in rule_birth}
        survive_set = {int(c) for c in rule_survive}

        new_grid = _gol_step(grid, birth_set, survive_set, wrap)

        # Update trail
        trail_length = getattr(params, 'trail_length', 30)
        trail_decay = getattr(params, 'trail_decay', 0.95)

        trail = trail * trail_decay
        trail[new_grid == 1] = trail_length
        trail = np.clip(trail, 0, trail_length)

        # Normalize trail for coloring
        normalized = trail / trail_length

        # Apply colormap
        colormap = getattr(params, 'trail_colormap', 'plasma')
        frame = apply_colormap(normalized, colormap)

        # Update state
        self._current_grid = new_grid
        self._current_trail = trail

        # Resize to requested output resolution
        if frame.shape[0] != params.height or frame.shape[1] != params.width:
            frame = cv2.resize(frame, (params.width, params.height), interpolation=cv2.INTER_NEAREST)  # type: ignore[assignment]

        return frame

    def validate_params(self, params: dict[str, Any]) -> GeneratorParams:
        return GameOfLifeParams(**params)
