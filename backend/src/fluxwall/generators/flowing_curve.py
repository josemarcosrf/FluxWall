"""Flowing Curve generator — animated complex-plane recurrences.

Ported from ``scripts/flowing_curve_demo.py``. Each curve is a cumulative sum
of complex ``dz = A * exp(1j * phi)`` steps, so the phase law ``phi(n, t)`` and
amplitude envelope ``A(n, t)`` pick the look. The ``uzumaki`` mode is the
signature spirograph-style spiral; the generic modes (linear, log, sqrt, sin,
golden, poly) sweep their phase with time to produce flowing filaments.

Frames are rasterized with a matplotlib ``FigureCanvasAgg`` at dpi=72 so the
``line_width`` parameter is expressed directly in device pixels.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from numpy.typing import NDArray

from fluxwall.core.models import FlowingCurveParams
from fluxwall.generators.base import Generator, GeneratorParams
from fluxwall.generators.registry import register_generator
from fluxwall.utils.colors import get_colormap

SUPPORTED_MODES = ('uzumaki', 'linear', 'log', 'sqrt', 'sin', 'golden', 'poly')


def _generate_generic(
    steps: int,
    step_size: float,
    omega: float,
    time_val: float,
    mode: str,
    exp: float = 0.5,
    mod_freq: float = 0.05,
    mod_amp: float = 0.5,
) -> NDArray[np.complex128]:
    """Build a generic flowing curve for the given phase mode.

    Args:
        steps: Number of integration steps.
        step_size: Base step magnitude.
        omega: Base angular frequency.
        time_val: Animation time value shifting the phase envelope.
        mode: Phase law: linear, log, sqrt, sin, golden, or poly.
        exp: Power exponent for the ``poly`` mode.
        mod_freq: Frequency of the amplitude/phase modulation.
        mod_amp: Depth of the amplitude/phase modulation.

    Returns:
        Complex curve array of shape ``(steps + 1,)``.
    """
    n = np.arange(1, steps + 1, dtype=np.float64)

    if mode == 'linear':
        phi = omega * n + time_val
    elif mode == 'log':
        phi = omega * np.log(n + 1) + time_val
    elif mode == 'sqrt':
        phi = omega * np.sqrt(n) + time_val
    elif mode == 'sin':
        phi = omega * n + mod_amp * np.sin(mod_freq * n + time_val)
    elif mode == 'golden':
        phi = omega * n * np.pi * (3 - np.sqrt(5)) + time_val
    elif mode == 'poly':
        phi = omega * (n**exp) + time_val
    else:
        raise ValueError(f'Unknown mode: {mode}')

    A = step_size * (1 + mod_amp * np.sin(mod_freq * n + time_val * 0.5))
    dz = A * np.exp(1j * phi)
    z = np.zeros(steps + 1, dtype=np.complex128)
    z[1:] = np.cumsum(dz)
    return z


def _generate_uzumaki(t: float, steps: int) -> NDArray[np.complex128]:
    """Build the signature uzumaki (whirlpool) curve at time *t*.

    Args:
        t: Animation time in ``[0, 1]``.
        steps: Number of integration steps (default 2000 in the demo).

    Returns:
        Complex curve array of shape ``(steps + 1,)``.
    """
    n = np.arange(1, steps + 1, dtype=np.float64)
    A = (steps - n) ** 1.5 / (1.5 * steps - n)
    inner = 10 * np.cos(100 * t) * np.sin(0.05 * n + 30 * t) + 10 * t
    phi = 2 * np.pi * t * inner - 1.8 * n * t + np.pi / 2
    dz = A * np.exp(1j * phi)
    z = np.zeros(steps + 1, dtype=np.complex128)
    z[1:] = np.cumsum(dz)
    return z


def _make_segments(x: NDArray[np.float64], y: NDArray[np.float64]) -> list[NDArray[np.float64]]:
    """Build a list of ``(2, 2)`` line segments from x/y coordinate arrays."""
    points = np.column_stack([x, y]).reshape(-1, 1, 2)
    seg_array = np.concatenate([points[:-1], points[1:]], axis=1)
    return list(seg_array)


def _auto_limits(
    zs: list[NDArray[np.complex128]],
    fig_size_px: tuple[int, int],
    padding: float = 0.08,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Compute plot limits that frame the curve while matching the figure aspect.

    Args:
        zs: Curve samples to frame.
        fig_size_px: Output figure size in pixels ``(width, height)``.
        padding: Fractional margin around the curve bounds.

    Returns:
        ``(x_lim, y_lim)`` tuples for the axes.
    """
    fig_w, fig_h = fig_size_px
    fig_aspect = fig_w / fig_h

    xs = np.concatenate([z.real for z in zs])
    ys = np.concatenate([z.imag for z in zs])
    x_min, x_max = xs.min(), xs.max()
    y_min, y_max = ys.min(), ys.max()
    x_span = max(x_max - x_min, 1e-10)
    y_span = max(y_max - y_min, 1e-10)
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2

    curve_aspect = x_span / y_span

    if curve_aspect > fig_aspect:
        x_span_final = x_span * (1 + padding)
        y_span_final = x_span_final / fig_aspect
    else:
        y_span_final = y_span * (1 + padding)
        x_span_final = y_span_final * fig_aspect

    return (
        (cx - x_span_final / 2, cx + x_span_final / 2),
        (cy - y_span_final / 2, cy + y_span_final / 2),
    )


def _render_frame(
    layers: list[tuple[NDArray[np.complex128], float]],
    x_lim: tuple[float, float],
    y_lim: tuple[float, float],
    cmap_name: str,
    time_val: float,
    line_width: float,
    alpha: float,
    fig_size_px: tuple[int, int],
) -> NDArray[np.uint8]:
    """Rasterize the curve layers into an RGB frame via matplotlib's Agg backend.

    ``layers`` is a list of ``(z, alpha_mult)`` pairs; earlier entries are drawn
    first (underneath) so a fading trail of sub-frame samples creates a
    motion-blur effect that smooths over fast temporal variation.

    Args:
        layers: Curve samples with per-layer alpha multipliers.
        x_lim: X-axis limits.
        y_lim: Y-axis limits.
        cmap_name: Matplotlib colormap name (supports FluxWall custom maps).
        time_val: Animation time used to shift colors along the curve.
        line_width: Line width in device pixels (dpi=72 rendering).
        alpha: Global line alpha.
        fig_size_px: Output frame size ``(width, height)``.

    Returns:
        RGB frame as uint8 array of shape ``(height, width, 3)``.
    """
    width, height = fig_size_px
    fig = Figure(figsize=(width / 72.0, height / 72.0), dpi=72)
    fig.patch.set_facecolor('black')
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_facecolor('black')
    ax.axis('off')
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)

    x0, x1 = x_lim
    y0, y1 = y_lim
    x_scale = width / (x1 - x0)
    y_scale = height / (y1 - y0)
    cmap = get_colormap(cmap_name)

    for z, alpha_mult in layers:
        px = (z.real - x0) * x_scale
        py = height - (z.imag - y0) * y_scale
        x = np.asarray(px)
        y = np.asarray(py)
        segments = _make_segments(x, y)
        n_seg = len(segments)

        idx = (np.linspace(0, 1, n_seg) + time_val) % 1.0
        colors = np.asarray(cmap(idx))
        colors[:, 3] *= alpha_mult

        ax.add_collection(LineCollection(segments, colors=colors, linewidth=line_width, alpha=alpha))

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    buffer = np.asarray(canvas.buffer_rgba())
    return np.ascontiguousarray(buffer[..., :3])


@register_generator
class FlowingCurveGenerator(Generator):
    """Animated flowing fractal curves from complex-plane recurrences."""

    name = 'flowing_curve'
    display_name = 'Flowing Curve'
    description = 'Animated complex-plane curves: uzumaki whirlpool, golden spiral, sine waves, and more'

    param_schema = {
        'type': 'object',
        'properties': {
            'width': {'type': 'integer', 'minimum': 100, 'maximum': 3000, 'default': 1170},
            'height': {'type': 'integer', 'minimum': 100, 'maximum': 5000, 'default': 2532},
            'fps': {'type': 'integer', 'minimum': 1, 'maximum': 60, 'default': 30},
            'duration_sec': {'type': 'number', 'minimum': 0.5, 'maximum': 30.0, 'default': 5.0},
            'colormap': {'type': 'string', 'default': 'magma'},
            'seed': {'type': ['integer', 'null'], 'default': None},
            'mode': {
                'type': 'string',
                'enum': ['uzumaki', 'linear', 'log', 'sqrt', 'sin', 'golden', 'poly'],
                'default': 'uzumaki',
            },
            'steps': {'type': 'integer', 'minimum': 500, 'maximum': 10000, 'default': 2000},
            'step_size': {'type': 'number', 'minimum': 0.0001, 'maximum': 1.0, 'default': 0.008},
            'omega': {'type': 'number', 'minimum': 0.0, 'maximum': 10.0, 'default': 0.15},
            'exp': {'type': 'number', 'minimum': 0.1, 'maximum': 10.0, 'default': 0.5},
            'mod_freq': {'type': 'number', 'minimum': 0.001, 'maximum': 5.0, 'default': 0.05},
            'mod_amp': {'type': 'number', 'minimum': 0.0, 'maximum': 2.0, 'default': 0.5},
            'line_width': {'type': 'number', 'minimum': 0.2, 'maximum': 10.0, 'default': 1.0},
            'alpha': {'type': 'number', 'minimum': 0.1, 'maximum': 1.0, 'default': 0.85},
            't_start': {'type': 'number', 'minimum': -2.0, 'maximum': 2.0, 'default': 0.0},
            't_end': {'type': 'number', 'minimum': -2.0, 'maximum': 2.0, 'default': 1.0},
            'supersample': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 16,
                'default': 1,
            },
            'blur_decay': {'type': 'number', 'minimum': 0.1, 'maximum': 1.0, 'default': 0.55},
            'auto_limits': {'type': 'boolean', 'default': True},
        },
        'required': ['width', 'height', 'fps', 'duration_sec'],
    }

    presets = {
        'uzumaki': {
            'name': 'Uzumaki',
            'description': 'Signature whirlpool spiral with a motion-blurred trail',
            'params': {
                'mode': 'uzumaki',
                'steps': 2000,
                'supersample': 8,
                'blur_decay': 0.55,
                'line_width': 1.0,
                'colormap': 'magma',
            },
        },
        'golden_spiral': {
            'name': 'Golden Spiral',
            'description': 'Golden-angle spiral with a serene sweeping phase',
            'params': {
                'mode': 'golden',
                'omega': 0.618,
                'step_size': 0.006,
                'steps': 2000,
                'colormap': 'viridis',
            },
        },
        'sine_flow': {
            'name': 'Sine Flow',
            'description': 'Flowing sine-modulated wave filaments',
            'params': {
                'mode': 'sin',
                'steps': 3000,
                'mod_amp': 0.5,
                'mod_freq': 0.05,
                'omega': 0.15,
                'colormap': 'plasma',
            },
        },
        'log_spiral': {
            'name': 'Log Spiral',
            'description': 'Logarithmic phase spiral',
            'params': {'mode': 'log', 'omega': 0.2, 'colormap': 'inferno'},
        },
        'poly_wave': {
            'name': 'Poly Wave',
            'description': 'Power-law phase sweep',
            'params': {'mode': 'poly', 'exp': 0.5, 'omega': 0.15, 'colormap': 'twilight'},
        },
        'sqrt_branch': {
            'name': 'Sqrt Branch',
            'description': 'Square-root phase curve',
            'params': {'mode': 'sqrt', 'omega': 0.2, 'colormap': 'cividis'},
        },
    }

    def generate_frame(self, frame_idx: int, params: GeneratorParams) -> NDArray[np.uint8]:
        """Generate a single RGB frame of a flowing curve.

        Args:
            frame_idx: Zero-based frame index.
            params: Generator parameters.

        Returns:
            RGB frame as uint8 array of shape ``(height, width, 3)``.
        """
        mode = getattr(params, 'mode', 'uzumaki')
        if mode not in SUPPORTED_MODES:
            raise ValueError(f'Unknown mode: {mode!r}; expected one of {", ".join(SUPPORTED_MODES)}')

        steps = int(getattr(params, 'steps', 2000))
        step_size = float(getattr(params, 'step_size', 0.008))
        omega = float(getattr(params, 'omega', 0.15))
        exp = float(getattr(params, 'exp', 0.5))
        mod_freq = float(getattr(params, 'mod_freq', 0.05))
        mod_amp = float(getattr(params, 'mod_amp', 0.5))
        line_width = float(getattr(params, 'line_width', 1.0))
        alpha = float(getattr(params, 'alpha', 0.85))
        t_start = float(getattr(params, 't_start', 0.0))
        t_end = float(getattr(params, 't_end', 1.0))
        supersample = int(getattr(params, 'supersample', 1))
        blur_decay = float(getattr(params, 'blur_decay', 0.55))
        auto_limits = bool(getattr(params, 'auto_limits', True))
        colormap = getattr(params, 'colormap', 'magma')

        total = max(params.total_frames - 1, 1)
        t = t_start + (t_end - t_start) * (frame_idx / total)

        def make_curve(tt: float) -> NDArray[np.complex128]:
            if mode == 'uzumaki':
                return _generate_uzumaki(tt, steps)
            return _generate_generic(steps, step_size, omega, tt * 10, mode, exp, mod_freq, mod_amp)

        if supersample > 1:
            t_prev = t_start + (t_end - t_start) * (max(frame_idx - 1, 0) / total)
            sub_ts = np.linspace(t_prev, t, supersample)
            zs = [make_curve(float(ts)) for ts in sub_ts]
            weights = [blur_decay ** (len(zs) - 1 - i) for i in range(len(zs))]
            layers = list(zip(zs, weights, strict=True))
        else:
            zs = [make_curve(t)]
            layers = [(zs[0], 1.0)]

        if auto_limits:
            x_lim, y_lim = _auto_limits(zs, (params.width, params.height))
        else:
            sample_ts = np.linspace(t_start, t_end, 16)
            sample_zs = [make_curve(float(tt)) for tt in sample_ts]
            x_lim, y_lim = _auto_limits(sample_zs, (params.width, params.height))

        return _render_frame(layers, x_lim, y_lim, colormap, t, line_width, alpha, (params.width, params.height))

    def validate_params(self, params: dict[str, Any]) -> GeneratorParams:
        return FlowingCurveParams(**params)
