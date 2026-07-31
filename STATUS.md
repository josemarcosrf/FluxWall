# FluxWall — Project Status

## Stack

Python 3.12, FastAPI, Streamlit, NumPy/Numba, OpenCV, pillow-heif, ffmpeg-python, uv, ruff, justfile, pytest, mypy

## Project Structure

```
src/fluxwall/
├── main.py                 # FastAPI entry + lifespan (calls discover_generators)
├── streamlit_app.py        # Streamlit UI (512 lines)
├── config.py               # Settings (pydantic-settings)
├── core/
│   ├── models.py           # Pydantic + dataclass schemas (GeneratorParams, ExportOptions, etc.)
│   ├── presets.py          # PresetRegistry
│   ├── exporters/          # video.py, heic.py, live_photo.py
│   └── job_queue.py        # Async job management (stub)
├── generators/
│   ├── base.py             # Generator ABC, GeneratorInfo, FrameBuffer
│   ├── registry.py         # GeneratorRegistry, @register_generator, discover_generators()
│   ├── game_of_life.py     # Numba JIT-accelerated GOL with trail rendering
│   ├── mandelbrot.py       # Numba parallel Mandelbrot with zoom/color cycling
│   ├── julia.py            # Julia set with spin/zoom/spin_zoom modes
│   ├── l_system.py         # Scaffolded
│   └── color_cycle.py      # Scaffolded
├── api/
│   ├── routes.py           # /health, /generators, /presets, /preview/stream, /export
│   ├── schemas.py          # Request/response models
│   └── websocket.py        # Stub
├── preview/
│   ├── mjpeg.py            # Stub
│   └── websocket.py        # Stub
└── utils/
    ├── colors.py           # Matplotlib colormap application
    ├── math.py             # Numba kernels (_gol_step, _mandelbrot_kernel, _julia_kernel)
    └── video.py            # frames_to_video (cv2), frames_to_video_ffmpeg
```

## Tests & Checks

| Check | Status |
|-------|--------|
| Tests | 15/15 passing (core models + generators) |
| Ruff format | 31 files formatted, 0 errors |
| Ruff lint | 0 errors |
| mypy | 10 errors (all expected: numba `prange`, stubs for ffmpeg/pillow-heif/OpenCV) |

## Running

```bash
just dev          # API (8000) + UI (8501) concurrently
just api          # API only
just ui           # UI only
```

## What's Implemented

### Generators (3/5 active)
- **Game of Life** — Numba JIT, configurable rules (B/S), wrap edges, trail rendering with colormaps, 7 patterns (random, gosper_gun, glider, pulsar, pentadecathlon, acorn, r_pentomino, diehard), trail decay
- **Mandelbrot Set** — Numba parallel, exponential zoom, smooth coloring, color cycling, configurable center/zoom/max_iter
- **Julia Set** — Numba parallel, 3 animation modes: `spin` (c rotates in circle), `zoom`, `spin_zoom`, configurable spin radius/speed, smooth coloring
- **L-System** — Scaffolded (generator class registered, no real rendering)
- **Color Cycle** — Scaffolded (generator class registered, no real rendering)

### Presets (9 JSON files)
- game_of_life: gosper_gun, glider_swarm, random_soup, pulsar, pentadecathlon, acorn, r_pentomino, diehard
- mandelbrot: classic, seahorse_valley, elephant_valley, triple_spiral, minibrot
- julia: douady_rabbit, dendrite, spiral, cauliflower, lightning, basilica, siegel_disk
- l_system: fractal_tree, barnsley_fern, dragon_curve, koch_snowflake, plant
- color_cycle: plasma, fire, aurora

### UI Features
- Sidebar: generator selection, preset loading, iPhone model picker, FPS/duration, colormap, seed, generator-specific widgets, export format/quality
- Preview: MJPEG streaming at 25% resolution for performance, phone-sized display (~400px max width), centered
- Export button (triggers API export, polls progress, download button)
- Parameter info expander showing types/ranges/defaults

## Known Issues

1. **L-System & Color Cycle are scaffolded** — registered but `generate_frame` returns blank frames
2. **Export job queue is a stub** — `/api/export/status` always returns `completed`, no real progress tracking
3. **WebSocket preview** — not implemented (MJPEG only)
4. **Live Photo export** — code exists but untested end-to-end
5. **mypy errors** — 10 expected (numba `prange`, missing stubs for ffmpeg/pillow-heif/OpenCV)
6. **Numba `reflected set` deprecation** — `_gol_step` uses Python sets which numba plans to deprecate (migration to numba.typed.Set pending)

## TODO / Next Steps

### High Priority
- [ ] **Implement L-System generator** — turtle-based fractal plant rendering with grow/rotate/wind animations
- [ ] **Implement Color Cycle generator** — procedural plasma/fire/aurora patterns
- [ ] **Export system** — real job queue with progress tracking, file download works (API polls status)
- [ ] **Mandelbrot/Julia presets auto-apply** — when switching generators, applied presets from a different generator should be cleared
- [ ] **"Time spiral" animation for Julia** — user requested a spiral path for `c` parameter (varying radius + angle over time)

### Medium Priority
- [ ] **WebSocket preview** — lower latency than MJPEG, bidirectional param updates
- [ ] **Numba reflected set fix** — migrate `_gol_step` to `numba.typed.Set` for forward compatibility
- [ ] **Test coverage** — add tests for API routes, export, preset loading
- [ ] **Docker optimization** — multi-stage build, smaller image
- [ ] **Error handling** — better Streamlit error messages when API returns 4xx
- [ ] **Parameter ranges** — add validation feedback in UI when params exceed schema bounds

### Low Priority
- [ ] **Keyboard shortcuts** — space to play/pause preview
- [ ] **Comparison view** — side-by-side before/after for param changes
- [ ] **Export history** — list of past exports with re-download
- [ ] **iOS Shortcut** — auto-apply exported Live Photo as wallpaper
- [ ] **Analytics** — count exports, popular presets

### Bugs Fixed in Previous Session
- Julia/Mandelbrot preview returning 400: `JuliaParams` & `GameOfLifeParams` missing fields that the param schema defined (`animation_mode`, `spin_radius`, `rule_birth`, `trail_decay`, etc.)
- Preview URL passing individual params instead of JSON `params` string
- `use_container_width` deprecated → `width='stretch'`
- `GameOfLifeGenerator.__init__()` missing `super().__init__()` call
- `@dataclass` missing on all `*Params` subclasses
- Extra blank lines after `@register_generator` decorators
