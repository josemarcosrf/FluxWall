"""Math utilities and Numba-accelerated kernels."""

from __future__ import annotations

import numpy as np
from numba import njit, prange
from numpy.typing import NDArray


@njit(parallel=True, cache=True)
def _gol_step(
    grid: NDArray[np.uint8],
    birth: set[int],
    survive: set[int],
    wrap: bool,
) -> NDArray[np.uint8]:
    """Single Game of Life step with custom rules."""
    h, w = grid.shape
    new_grid = np.zeros_like(grid)

    for y in prange(h):
        for x in range(w):
            # Count neighbors
            count = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    ny = (y + dy) % h if wrap else y + dy
                    nx = (x + dx) % w if wrap else x + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        count += grid[ny, nx]

            # Apply rules
            if grid[y, x]:
                new_grid[y, x] = 1 if count in survive else 0
            else:
                new_grid[y, x] = 1 if count in birth else 0

    return new_grid


@njit(parallel=True, cache=True)
def _mandelbrot_kernel(
    re: NDArray[np.float64],
    im: NDArray[np.float64],
    max_iter: int,
    smooth: bool,
) -> NDArray[np.float64]:
    """Mandelbrot iteration kernel."""
    h, w = len(im), len(re)
    result = np.zeros((h, w), dtype=np.float64)

    for i in prange(h):
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
                zn = x * x + y * y
                if zn > 0:
                    mu = iter_count + 1 - np.log(np.log(zn)) / np.log(2)
                    result[i, j] = mu
                else:
                    result[i, j] = iter_count
            else:
                result[i, j] = iter_count

    return result


@njit(parallel=True, cache=True)
def _julia_kernel(
    re: NDArray[np.float64],
    im: NDArray[np.float64],
    c_real: float,
    c_imag: float,
    max_iter: int,
    smooth: bool,
) -> NDArray[np.float64]:
    """Julia set iteration kernel."""
    h, w = len(im), len(re)
    result = np.zeros((h, w), dtype=np.float64)

    for i in prange(h):
        cy = im[i]
        for j in range(w):
            cx = re[j]
            x = cx
            y = cy
            iter_count = 0

            for _ in range(max_iter):
                x2 = x * x
                y2 = y * y
                if x2 + y2 > 4.0:
                    break
                y = 2.0 * x * y + c_imag
                x = x2 - y2 + c_real
                iter_count += 1

            if smooth and iter_count < max_iter:
                zn = x * x + y * y
                if zn > 0:
                    mu = iter_count + 1 - np.log(np.log(zn)) / np.log(2)
                    result[i, j] = mu
                else:
                    result[i, j] = iter_count
            else:
                result[i, j] = iter_count

    return result


@njit(cache=True)
def _simplex_noise_2d(
    x: float,
    y: float,
    seed: int = 0,
) -> float:
    """Simple 2D noise function for procedural generation."""
    # Simple hash-based noise
    n = int(x * 12345.6789 + y * 98765.4321 + seed * 42.0) & 0x7FFFFFFF
    n = (n ^ (n >> 13)) * 0x5BD1E995
    n = n ^ (n >> 15)
    return (n & 0xFFFF) / 65535.0


@njit(parallel=True, cache=True)
def _fbm_2d(
    x_coords: NDArray[np.float64],
    y_coords: NDArray[np.float64],
    octaves: int,
    persistence: float,
    lacunarity: float,
    seed: int,
) -> NDArray[np.float64]:
    """Fractal Brownian Motion 2D noise."""
    h, w = len(y_coords), len(x_coords)
    result = np.zeros((h, w), dtype=np.float64)

    amplitude = 1.0
    frequency = 1.0
    max_value = 0.0

    for _ in range(octaves):
        for i in prange(h):
            for j in range(w):
                nx = x_coords[j] * frequency
                ny = y_coords[i] * frequency
                result[i, j] += _simplex_noise_2d(nx, ny, seed) * amplitude

        max_value += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    # Normalize
    if max_value > 0:
        result /= max_value

    return result


def load_rle_pattern(
    pattern_name: str,
    grid: NDArray[np.uint8],
    grid_h: int,
    grid_w: int,
    scale: float = 1.0,
) -> None:
    """Load a named RLE pattern into the grid."""
    patterns = {
        'gosper_gun': ('24o$22bobo$12b2o6b2o$11bo3bo4b2o$10bo5bo$10bo5bo$10bo3b2o$11bo3bo$12b2o!', 40, 30),
        'glider': ('bo$2bo$3o!', 3, 3),
        'pulsar': (
            '2bo7bo2$2bo7bo2$2bo7bo2$14bo$13bobo$13bobo$14bo2$14bo$13bobo$13bobo$14bo2$2bo7bo2$2bo7bo2$2bo7bo!',
            17,
            17,
        ),
        'acorn': ('5bobo$2b2o$bo2bo$2b2o$3bo!', 7, 5),
        'r_pentomino': ('2bo$2bo$bo!', 3, 3),
        'pentadecathlon': ('8bo$7bobo$7bobo$8bo2$8bo$7bobo$7bobo$8bo!', 10, 9),
        'diehard': ('6bo$bo$obo$bo2bo$2b3o!', 6, 5),
    }

    if pattern_name not in patterns:
        return

    rle, pat_w, pat_h = patterns[pattern_name]

    # Parse simple RLE
    y, x = (grid_h - int(pat_h * scale)) // 2, (grid_w - int(pat_w * scale)) // 2
    row, col = 0, 0
    count = ''

    for char in rle:
        if char.isdigit():
            count += char
        elif char == 'b':
            n = int(count) if count else 1
            col += int(n * scale)
            count = ''
        elif char == 'o':
            n = int(count) if count else 1
            for i in range(int(n * scale)):
                gy, gx = y + int(row * scale), x + col + i
                if 0 <= gy < grid_h and 0 <= gx < grid_w:
                    grid[gy, gx] = 1
            col += int(n * scale)
            count = ''
        elif char == '$':
            row += 1
            col = 0
            count = ''
        elif char == '!':
            break


def parse_rule_string(rule: str) -> tuple[set[int], set[int]]:
    """Parse B3/S23 style rule string into birth/survive sets."""
    if '/' not in rule:
        return {3}, {2, 3}

    birth_part, survive_part = rule.split('/')
    birth = {int(c) for c in birth_part if c.isdigit() and birth_part.startswith('B')}
    survive = {int(c) for c in survive_part if c.isdigit() and survive_part.startswith('S')}

    return birth, survive
