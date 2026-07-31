"""FluxWall Generators Package.

Available generators:
- game_of_life: Conway's Game of Life with color trails
- mandelbrot: Mandelbrot set with zoom animation
- julia: Julia set with spin/zoom animation
- l_system: L-system fractal plants (scaffolded)
- color_cycle: Parametric color cycling patterns (scaffolded)
"""

from fluxwall.generators.registry import discover_generators, registry

__all__ = [
    'registry',
    'discover_generators',
]
