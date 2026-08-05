#!/usr/bin/env python3
"""Flowing fractal curve animation — complex-plane recurrences via matplotlib.

Usage:
  python scripts/flowing_curve_demo.py --mode uzumaki
  python scripts/flowing_curve_demo.py --mode sin --steps 3000 --seconds 8 --cmap plasma
  python scripts/flowing_curve_demo.py --mode golden --omega 0.618 --cmap viridis
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from numpy.typing import NDArray

# ── Helpers ──────────────────────────────────────────────────────────────────

def make_segments(x: NDArray[np.float64], y: NDArray[np.float64]) -> NDArray[np.float64]:
    points = np.column_stack([x, y]).reshape(-1, 1, 2)
    return np.concatenate([points[:-1], points[1:]], axis=1)


def fmt_num(x: float) -> str:
    """Compact string for a float, e.g. 0.30 -> '0.3', 2.0 -> '2'."""
    return f'{x:.3f}'.rstrip('0').rstrip('.')


def build_output_tag(args: argparse.Namespace) -> str:
    """Encode the parameters most relevant to how a render looks/plays into a filename tag."""
    parts = [f't{fmt_num(args.t_start)}-{fmt_num(args.t_end)}']
    parts.append(f'{fmt_num(args.seconds)}s')
    parts.append(f'{args.fps}fps')
    if args.speed != 1.0:
        parts.append(f'speed{fmt_num(args.speed)}')
    if args.adaptive:
        parts.append(f'adaptive{fmt_num(args.adaptive_strength)}')
    if args.supersample > 1:
        parts.append(f'ss{args.supersample}')
    return '_'.join(parts)


# ── Curve generators ─────────────────────────────────────────────────────────

def generate_generic(
    steps: int,
    step_size: float,
    omega: float,
    time_val: float,
    mode: str,
    exp: float = 0.5,
    mod_freq: float = 0.05,
    mod_amp: float = 0.5,
) -> NDArray[np.complex128]:
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
        phi = omega * (n ** exp) + time_val
    else:
        raise ValueError(f'Unknown mode: {mode}')

    A = step_size * (1 + mod_amp * np.sin(mod_freq * n + time_val * 0.5))
    dz = A * np.exp(1j * phi)
    z = np.zeros(steps + 1, dtype=np.complex128)
    z[1:] = np.cumsum(dz)
    return z


def generate_uzumaki(t: float) -> NDArray[np.complex128]:
    n = np.arange(1, 2001, dtype=np.float64)
    A = (2000 - n) ** 1.5 / (3000 - n)
    inner = 10 * np.cos(100 * t) * np.sin(0.05 * n + 30 * t) + 10 * t
    phi = 2 * np.pi * t * inner - 1.8 * n * t + np.pi / 2
    dz = A * np.exp(1j * phi)
    z = np.zeros(2001, dtype=np.complex128)
    z[1:] = np.cumsum(dz)
    return z


# ── Adaptive time mapping ────────────────────────────────────────────────────

def build_adaptive_timemap(
    make_curve, total_frames: int, fine_steps: int = 3000,
    compression: float = 0.3, t_start: float = 0.0, t_end: float = 1.0,
) -> NDArray[np.float64]:
    """Build a CDF-based time mapping that concentrates frames where the curve
    changes fastest.

    Parameters
    ----------
    make_curve:
        Function ``f(t: float) -> NDArray`` returning the curve at time *t*.
    total_frames:
        Number of output frames.
    fine_steps:
        Resolution of the change-rate scan.
    compression:
        Power applied to the change signal before building the CDF.
        ``0.0`` → uniform stepping (no adaptation),
        ``1.0`` → fully adaptive (can cluster extremely).
        Values around 0.2–0.4 give a gentler distribution.
    t_start, t_end:
        Sub-range of *t* to scan and render.
    """
    t_fine = np.linspace(t_start, t_end, fine_steps)
    deltas = np.zeros(fine_steps)
    z_prev = make_curve(t_fine[0])
    for i in range(1, fine_steps):
        z_curr = make_curve(t_fine[i])
        deltas[i] = np.mean(np.abs(z_curr - z_prev) ** 2)
        z_prev = z_curr

    # Smooth the change signal to avoid jitter
    kernel = np.ones(11) / 11
    deltas = np.convolve(deltas, kernel, mode='same')
    deltas[0] = deltas[1]

    # Guard: if everything is static, fall back to uniform over [t_start, t_end]
    if deltas.sum() < 1e-12:
        return np.linspace(t_start, t_end, total_frames)

    # Apply compression to tame extreme clustering
    compressed = deltas ** compression

    cdf = np.cumsum(compressed)
    cdf /= cdf[-1]
    return np.interp(np.linspace(0, 1, total_frames), cdf, t_fine)


# ── Auto-limits ──────────────────────────────────────────────────────────────

def auto_limits(
    zs: list[NDArray[np.complex128]],
    fig_size_px: tuple[int, int] = (1920, 1080),
    padding: float = 0.08,
) -> tuple[tuple[float, float], tuple[float, float]]:
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


# ── Rendering ────────────────────────────────────────────────────────────────

def render_frame(
    ax: matplotlib.axes.Axes,
    layers: list[tuple[NDArray[np.complex128], float]],
    x_lim: tuple[float, float],
    y_lim: tuple[float, float],
    cmap_name: str,
    time_val: float,
    line_width: float = 0.6,
    alpha: float = 0.85,
) -> None:
    """Render one or more curves into the same frame.

    ``layers`` is a list of ``(z, alpha_mult)`` pairs; earlier entries are
    drawn first (underneath) so a fading trail of sub-frame samples creates a
    motion-blur effect that smooths over fast temporal variation.
    """
    ax.clear()
    ax.set_xlim(x_lim)
    ax.set_ylim(y_lim)

    for z, alpha_mult in layers:
        x, y = z.real, z.imag
        segments = make_segments(x, y)
        n_seg = len(segments)

        idx = (np.linspace(0, 1, n_seg) + time_val) % 1.0
        colors = plt.colormaps[cmap_name](idx)
        colors[:, 3] *= alpha_mult

        ax.add_collection(LineCollection(segments, colors=colors, linewidth=line_width, alpha=alpha))


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description='Flowing fractal curve animation')
    p.add_argument('--mode', default='sin', choices=[
        'uzumaki', 'linear', 'log', 'sqrt', 'sin', 'golden', 'poly',
    ], help='Curve mode (default: sin)')
    p.add_argument('--steps', type=int, default=2000, help='Iterations per frame')
    p.add_argument('--step-size', type=float, default=0.008)
    p.add_argument('--omega', type=float, default=0.15)
    p.add_argument('--exp', type=float, default=0.5)

    p.add_argument('--seconds', type=float, default=5.0,
                   help='Target real-world playback length in seconds, before --speed is '
                        'applied (default: 5)')
    p.add_argument('--fps', type=int, default=30,
                   help='Output video frame rate (default: 30)')
    p.add_argument('--speed', type=float, default=1.0,
                   help='Frame-count multiplier: total_frames = fps * seconds * speed, and '
                        'actual video length = seconds * speed. Values >1 add frames AND '
                        'stretch the video over more real time, so the same t-range unfolds '
                        'more slowly and with finer time resolution (default: 1)')
    p.add_argument('--adaptive', action='store_true',
                   help='Redistribute the (fixed) frame budget non-uniformly across the '
                        't-range, spending more frames where the curve changes fastest and '
                        'fewer where it is calm, instead of stepping t uniformly. Use with '
                        '--adaptive-strength. Does not add frames, only reallocates them')
    p.add_argument('--adaptive-strength', type=float, default=0.3,
                   help='Adaptive clustering strength 0-1 (default: 0.3; 0=uniform stepping, '
                        '1=aggressive clustering onto fast-changing moments)')
    p.add_argument('--t-start', type=float, default=0.0,
                   help='Start of the t range to render. Narrow this together with --t-end '
                        'to "zoom" into a specific slice of time instead of rendering the '
                        'full curve span (default: 0.0)')
    p.add_argument('--t-end', type=float, default=1.0,
                   help='End of the t range to render. See --t-start (default: 1.0)')
    p.add_argument('--cmap', default='magma', help='Matplotlib colormap')
    p.add_argument('--supersample', type=int, default=1,
                   help='Sub-samples per output frame, blended with a fading trail '
                        '(motion blur) to smooth fast temporal variation, e.g. in '
                        '"uzumaki" mode. Blends within an already-placed frame; it does '
                        'not change frame timing/placement (use --speed or --t-start/--t-end '
                        'for that). 1 = off (default). Try 6-10 for uzumaki.')
    p.add_argument('--blur-decay', type=float, default=0.55,
                   help='Alpha falloff per trailing sub-sample when --supersample > 1 '
                        '(default: 0.55; lower = shorter, sharper trail)')

    p.add_argument('--width', type=int, default=1920)
    p.add_argument('--height', type=int, default=1080)
    p.add_argument('--line-width', type=float, default=0.6)
    p.add_argument('--alpha', type=float, default=0.85)

    p.add_argument('--output', default='output', help='Output directory')
    p.add_argument('--no-video', action='store_true', help='Skip ffmpeg encoding')
    p.add_argument('--keep-frames', action='store_true', help='Keep PNG frames after encoding')
    args = p.parse_args()

    if args.width % 2 != 0 or args.height % 2 != 0:
        raise SystemExit(
            'Error: --width and --height must both be even for H.264/yuv420p '
            f'encoding (got {args.width}x{args.height}); '
            'an odd dimension will fail at the ffmpeg encode step.'
        )

    out_dir = Path(args.output)
    frames_dir = out_dir / '_frames'
    frames_dir.mkdir(parents=True, exist_ok=True)

    base_frames = int(args.fps * args.seconds)
    total_frames = max(1, int(base_frames * args.speed))
    is_uzumaki = args.mode == 'uzumaki'
    fig_size = (args.width / 100, args.height / 100)

    fig, ax = plt.subplots(figsize=fig_size, dpi=100)
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')
    ax.set_aspect('equal')
    ax.axis('off')
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

    # Pick the generator function for reuse
    def make_curve(t: float) -> NDArray[np.complex128]:
        return generate_uzumaki(t) if is_uzumaki else generate_generic(
            args.steps, args.step_size, args.omega, t * 10, args.mode, args.exp,
        )

    # Build adaptive time map (or uniform)
    if args.adaptive:
        print('  Building adaptive time map…', end=' ', flush=True)
        t_map = build_adaptive_timemap(
            make_curve, total_frames, compression=args.adaptive_strength,
            t_start=args.t_start, t_end=args.t_end,
        )
        print('ok')
    else:
        t_map = np.linspace(args.t_start, args.t_end, total_frames)

    print(f'  Mode:   {args.mode}')
    print(f'  Frames: {total_frames} (base {base_frames} × speed {args.speed})')
    print(f'  t range: [{args.t_start}, {args.t_end}]')
    if args.adaptive:
        print(f'  Stepping: adaptive (strength {args.adaptive_strength})')
    if args.supersample > 1:
        print(f'  Supersample: {args.supersample}x (blur decay {args.blur_decay})')
    print(f'  Output: {out_dir.resolve()}')
    print()

    t_start = time.perf_counter()

    for idx in range(total_frames):
        t = float(t_map[idx])

        if args.supersample > 1:
            t_prev = float(t_map[idx - 1]) if idx > 0 else t
            sub_ts = np.linspace(t_prev, t, args.supersample)
            zs = [make_curve(float(ts)) for ts in sub_ts]
            # Newest sample (index -1) is fully opaque; older ones fade out.
            weights = [args.blur_decay ** (len(zs) - 1 - i) for i in range(len(zs))]
            layers = list(zip(zs, weights))
        else:
            zs = [make_curve(t)]
            layers = [(zs[0], 1.0)]

        # Per-frame auto-limits so the curve always fills the frame pleasantly
        x_lim, y_lim = auto_limits(zs, (args.width, args.height))

        render_frame(ax, layers, x_lim, y_lim, args.cmap, t, args.line_width, args.alpha)
        fig.savefig(frames_dir / f'frame_{idx:05d}.png',
                    dpi=100, facecolor='black', edgecolor='none', pad_inches=0)

        elapsed = time.perf_counter() - t_start
        rate = (idx + 1) / elapsed
        eta = (total_frames - idx - 1) / rate
        sys.stdout.write(f'\r  [{idx + 1}/{total_frames}]  {rate:.1f} fps  ETA {eta:.0f}s  ')
        sys.stdout.flush()

    elapsed = time.perf_counter() - t_start
    print(f'\n  Done — {total_frames} frames in {elapsed:.1f}s ({total_frames/elapsed:.1f} fps)')

    # Encode video
    if not args.no_video:
        ts = time.strftime('%Y%m%d_%H%M%S')
        tag = build_output_tag(args)
        video_path = out_dir / f'flowing_curve_{args.mode}_{tag}_{ts}.mp4'
        print(f'  Encoding: {video_path} …', end=' ', flush=True)
        subprocess.run([
            'ffmpeg', '-y',
            '-framerate', str(args.fps),
            '-i', str(frames_dir / 'frame_%05d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'medium',
            '-crf', '18',
            str(video_path),
        ], check=True, capture_output=True)
        print('ok')

    if not args.keep_frames:
        shutil.rmtree(frames_dir)


if __name__ == '__main__':
    main()
