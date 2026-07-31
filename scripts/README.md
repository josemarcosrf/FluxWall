# Flowing Fractal Curve Demo

Self-contained Python script for animating complex-plane recurrences. Uses
NumPy (vectorized), Matplotlib (`LineCollection`), and FFmpeg.

## Usage

```bash
# Run from project root with uv
uv run scripts/flowing_curve_demo.py --mode prescribed

# Or with pip-installed deps
python scripts/flowing_curve_demo.py --mode sin --seconds 8 --cmap plasma
```

## Modes

### `prescribed` (default-ish)

Your specific recurrence:

```
z_{n+1} = z_n + (2000-n)^{3/2} / (3000-n)
          · exp{i[2πt(10cos(100t)sin(0.05n+30t) + 10t) - 1.8nt + π/2]}
```

with `z_1 = 0`, `n = 1..2000`, `t ∈ [0,1]`. Parameters are hard-coded.
Dense, rapidly evolving tangle with dramatic scale changes over time.

### `sin`

Tangly, kelp-like tendrils that wave and drift.
```
φ = ω·n + A·sin(k·n + t)
```

### `linear`

Precessing Archimedean spiral.
```
φ = ω·n + t
```

### `log`

Tight logarithmic whorls that bloom outward.
```
φ = ω·log(n+1) + t
```

### `sqrt`

Wide sweeping arcs, comet-like tails.
```
φ = ω·√n + t
```

### `golden`

Phyllotaxis-inspired branching (golden-angle adjacent).
```
φ = ω·n·π·(3-√5) + t
```

### `poly`

Power-law spiral; varies from asteroid-belt rings to star-shaped bursts.
```
φ = ω·n^p + t
```

## All CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `sin` | One of `prescribed`, `linear`, `log`, `sqrt`, `sin`, `golden`, `poly` |
| `--steps` | `2000` | Iterations per frame (ignored in `prescribed`) |
| `--step-size` | `0.008` | Base step magnitude (ignored in `prescribed`) |
| `--omega` | `0.15` | Angular frequency (ignored in `prescribed`) |
| `--exp` | `0.5` | Power exponent for `poly` mode |
| `--seconds` | `5.0` | Animation duration |
| `--fps` | `30` | Frames per second |
| `--speed` | `1.0` | Speed multiplier (>1 = more frames, slower motion) |
| `--adaptive` | — | Distribute frames proportional to curve change rate |
| `--adaptive-strength` | `0.3` | Clustering strength 0–1 (0=uniform, 1=aggressive) |
| `--t-start` | `0.0` | Start of t range (zoom into a sub-interval) |
| `--t-end` | `1.0` | End of t range |
| `--cmap` | `magma` | Matplotlib colormap |
| `--width` | `1920` | Frame width |
| `--height` | `1080` | Frame height |
| `--line-width` | `0.6` | Line width in points |
| `--alpha` | `0.85` | Line alpha |
| `--output` | `output` | Output directory |
| `--no-video` | — | Skip ffmpeg encoding, just save PNGs |
| `--keep-frames` | — | Don't delete PNG frames after encoding |

## Examples

```bash
# Prescribed formula with adaptive timing (smoother transitions)
uv run scripts/flowing_curve_demo.py --mode prescribed --adaptive --seconds 8

# Prescribed formula at 2× speed (twice as many frames, half-speed playback)
uv run scripts/flowing_curve_demo.py --mode prescribed --speed 2.0

# Zoom into the most active range [0.6, 0.8] with 5× temporal resolution
uv run scripts/flowing_curve_demo.py --mode prescribed --t-start 0.6 --t-end 0.8 --adaptive

# Psychedelic sin mode at higher res
uv run scripts/flowing_curve_demo.py --mode sin --steps 3000 --seconds 8 --cmap plasma --line-width 0.4

# Precessing logarithmic spiral
uv run scripts/flowing_curve_demo.py --mode log --omega 2.0 --step-size 0.02 --cmap viridis

# Phyllotaxis branching
uv run scripts/flowing_curve_demo.py --mode golden --omega 0.618 --step-size 0.015 --cmap twilight

# Generate frames only (no video)
uv run scripts/flowing_curve_demo.py --mode sqrt --seconds 3 --no-video
```

## Dependencies

- Python ≥ 3.12
- NumPy, Matplotlib
- FFmpeg (for video encoding; skip with `--no-video`)
