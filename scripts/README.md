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

---

# MP4 → iOS Live Photo

[`mp4_to_live_photo.py`](mp4_to_live_photo.py) converts a `flowing_curve_demo.py`
MP4 into a **Live Photo bundle** (`still.heic` + `motion.mov` + matching
`ContentIdentifier` metadata + `manifest.json` + `.pvt`), which you import into
Photos on this Mac and set on an iPhone as a lock-screen **Live Wallpaper**
(press-and-hold to animate).

## How it works

iOS treats "Live Wallpapers" as **Live Photos**: a still image + motion video
pair that share the same `ContentIdentifier` UUID.

- The **image** stores it in its Apple MakerNote (key `17`) — written with
  [`makelive`](https://github.com/RhetTbull/makelive) (macOS CoreGraphics).
- The **video** stores it in QuickTime movie metadata — also stamped by
  `makelive` (AVFoundation), preserving the track structure.
- The **video** also carries two `mebx` timed-metadata tracks, copied from a real
  iPhone Live Photo (`scripts/_mebx_template.json`, extracted from
  `vendor-livp/IMG_7673.MOV`):
  - `com.apple.quicktime.live-photo-info`: one 144-byte sample per video frame,
    minus a fixed 3-frame (~0.05s) lead-in gap — real Live Photos (and other
    working converters) never cover the very start of the video with this
    track, only the last ~95% of it.
  - `com.apple.quicktime.still-image-time`: a single 89-byte sample at the still
    frame's position (via a leading empty edit), marking the cover moment.
    Defaults to the clip's midpoint, matching every working reference file
    inspected.
  Getting the pairing right (`ContentIdentifier` + both tracks present) is
  enough for Photos itself to show the "LIVE" badge and animate on
  long-press — but the Lock Screen wallpaper picker applies its own,
  stricter check on top and will still report **"Motion Not Available"**
  even when Photos plays the Live Photo fine. Matching the exact resolution,
  frame rate, and duration of a real, confirmed-working Live Photo mattered
  here — see `--fps`/`--duration` defaults below.

`ffmpeg` handles only the video transcode — it cannot write `mebx` tracks (it
drops them even on `-c copy`), so `inject_mebx_tracks()` re-muxes the finished
MOV byte-for-byte (no re-encode): the video `mdat` and track are copied
verbatim and the two metadata tracks are rebuilt with fresh sample tables
(`stts`/`stsc`/`stsz`/`stco`) sized for the output frame count/rate, reusing
the template's static boxes (`stsd`, `hdlr`, `gmhd`, `dref`) and sample bytes
unchanged. pillow-heif handles only the HEIC still; `makelive` stamps the
shared `ContentIdentifier` into both files and packages the `.pvt`.

## Install

```bash
uv sync --extra livephoto   # macOS only (CoreGraphics/AVFoundation)
```

## Usage

```bash
uv run scripts/mp4_to_live_photo.py output/flowing_curve_....mp4
```

### Time mapping (speed / slow-motion)

The source MP4s are high-fps (e.g. 240fps, often with an adaptive time map baked
in). Re-timing to a Live Photo never changes wall-clock speed or the relative
fast/slow character of the animation — but a plain 240→30fps downsample **drops
~8 of every 9 frames**, so fine micro-motion gets coarser. Use these flags to
pick *which* part to feature and at what tempo:

| Flag | Default | Meaning |
|------|---------|---------|
| `--start-sec` | `0` | Where in the source to start the clip |
| `--duration` | `3` | Live Photo length. **Only 1s is confirmed to work as a Lock Screen wallpaper** — 2s and 3s produced valid, playable Live Photos in Photos but the Lock Screen picker still reported "Motion Not Available". Cause not yet root-caused (possibly a real duration cap, possibly the fixed lead-gap needing to scale with duration instead — see `inject_mebx_tracks()`). |
| `--speed` | `1` | Tempo vs source: `1` = same, `0.5` = 2× slow-mo, `2` = 2× fast |
| `--fps` | `60` | Output frame rate, matches the confirmed-working reference |
| `--interpolate` | off | Blend frames when resampling instead of dropping — smoother when downsampling a high-fps source |

The clip is the source window `[--start-sec, --start-sec + --duration × --speed]`,
re-mapped onto `--duration` seconds. So slow-mo of a busy region is:
`--start-sec 1.0 --speed 0.5 --duration 3` (1.5s of source stretched to 3s).

### Resolution (`--width`/`--height`/`--model`)

Defaults to **1080 × 1920** — not any real iPhone screen resolution, but the
exact size of a real Live Photo pair (`vendor-livp/IMG_7725.MOV`/`.HEIC`)
confirmed to work as a Lock Screen wallpaper. Override with `--width W
--height H` (both required; rounded down to even), or pick a device preset:

| Model | Resolution |
|-------|------------|
| `pro-max` | 1290 × 2796 |
| `pro` | 1179 × 2556 |
| `pro-old` | 1170 × 2532 |
| `se` | 750 × 1334 |

### Examples

```bash
# Default: first 3s of the source at 1080x1920/60fps (2s/3s not confirmed working — see above)
uv run scripts/mp4_to_live_photo.py output/flowing_curve_....mp4

# Confirmed-working config: 1s clip, source window centered on t=1s
uv run scripts/mp4_to_live_photo.py output/flowing_curve_....mp4 --duration 1 --start-sec 0.5

# 2× slow-motion of source [1s, 2.5s], motion-interpolated
uv run scripts/mp4_to_live_photo.py output/flowing_curve_....mp4 \
  --start-sec 1.0 --speed 0.5 --interpolate

# Hardware encoder (macOS VideoToolbox) for faster encodes
uv run scripts/mp4_to_live_photo.py output/flowing_curve_....mp4 --codec hevc_videotoolbox
```

### Import to iPhone

Double-click the `.pvt` package on this Mac — Photos imports it as a Live
Photo. Let iCloud Photos sync it to your iPhone, then set it from the Lock
Screen wallpaper picker (it animates on press-and-hold).

A `.pvt` is a folder (Finder shows it as a single file) containing
`metadata.plist` plus the stamped still/motion pair; `makelive` builds it from
the same pair, so the import is guaranteed.

### Output

```
output/<name>_livephoto/
├── still.heic       # HEIC still with MakerNote ContentIdentifier
├── motion.mov       # HEVC (hvc1) portrait MOV with matching identifier
└── manifest.json    # bundle metadata (project convention)
output/<name>_livephoto.pvt    # macOS Photos import package (double-click)
```

## Dependencies (this script)

- Python ≥ 3.12, NumPy, Pillow, pillow-heif (project deps)
- FFmpeg + ffprobe
- `makelive` (optional extra `livephoto`, macOS only)
