# FluxWall — Project Status

## Stack

Backend: Python 3.12, FastAPI, Streamlit, NumPy/Numba, OpenCV, pillow-heif, ffmpeg-python, uv, ruff, justfile, pytest, mypy, httpx

Webapp: React 19, Vite 8, TypeScript, react-router-dom 7, oxlint

## Project Structure

```
src/fluxwall/
├── main.py                 # FastAPI entry + lifespan; mounts webapp/dist (SPA) at /
├── streamlit_app.py        # Streamlit UI (530 lines)
├── config.py               # Settings (pydantic-settings)
├── core/
│   ├── models.py           # Pydantic + dataclass schemas (GeneratorParams, ExportOptions, ExportJob, ...)
│   ├── presets.py          # PresetRegistry
│   ├── exporters/          # video.py, heic.py, live_photo.py
│   └── job_queue.py        # Real async job queue (worker pool, progress/status tracking)
├── generators/
│   ├── base.py             # Generator ABC, GeneratorInfo, FrameBuffer
│   ├── registry.py         # GeneratorRegistry, @register_generator, discover_generators()
│   ├── game_of_life.py     # Numba JIT-accelerated GOL with trail rendering
│   ├── mandelbrot.py       # Numba parallel Mandelbrot with zoom/color cycling
│   ├── julia.py            # Julia set with spin/zoom/spin_zoom modes
│   ├── flowing_curve.py    # Complex-plane recurrence curves (uzumaki, sin, golden, log, sqrt, poly)
│   ├── l_system.py         # Scaffolded
│   └── color_cycle.py      # Scaffolded
├── api/
│   ├── routes.py           # /health, /generators, /presets, /preview/start, /preview/stream, /export, /export/status|download
│   ├── schemas.py          # Request/response models
│   └── websocket.py        # Real-time frame streaming (active)
├── preview/
│   ├── mjpeg.py            # Real MJPEG builder (generate_mjpeg_stream)
│   └── websocket.py        # Stub / placeholder
└── utils/
    ├── colors.py           # Matplotlib colormap application
    ├── math.py             # Numba kernels (_gol_step, _mandelbrot_kernel, _julia_kernel)
    └── video.py            # frames_to_video (cv2), frames_to_video_ffmpeg

webapp/                     # React 19 + Vite + TS SPA (served by FastAPI at /)
├── src/pages/              # Discover, Studio, Library
├── src/components/         # TopBar, PreviewCanvas, StillThumb, PhoneFrame, ParamField, OutputForm, ExportPanel, Rail, ui
└── src/lib/                # data, render (JS ports of generator math), exports, store, glyphs, types, api
```

## Tests & Checks

| Check | Status |
|-------|--------|
| Tests | 36/36 passing (models, generators, job queue, live photo, export API e2e) |
| Ruff format | clean |
| Ruff lint | 0 errors |
| mypy (src) | 0 errors |

## Running

```bash
just dev                # API (8000) + React webapp dev server (Vite, HMR, -> http://localhost:5173)
just api                # API only
just ui                 # Streamlit UI only (legacy)
just webapp-dev         # Vite dev server (webapp/) pointed at a local API on :8000
just check              # ruff format + lint + mypy
just test               # pytest
```

## What's Implemented

### Generators (4/6 active)
- **Game of Life** — Numba JIT, configurable rules (B/S), wrap edges, trail rendering with colormaps, 8 patterns (random, gosper_gun, glider, pulsar, pentadecathlon, acorn, r_pentomino, diehard), trail decay
- **Mandelbrot Set** — Numba parallel, exponential zoom, smooth coloring, color cycling, configurable center/zoom/max_iter
- **Julia Set** — Numba parallel, 3 animation modes: `spin`, `zoom`, `spin_zoom`, configurable spin radius/speed, smooth coloring
- **Flowing Curves** — complex-plane recurrence curves (JS port in webapp + Python generator), modes: uzumaki/sin/linear/log/sqrt/golden/poly
- **L-System** — Scaffolded (registered, no real rendering)
- **Color Cycle** — Scaffolded (registered, no real rendering)

### Export System (now real, was a stub)
- Async job queue (`job_queue.py`) with a worker pool; `_execute_job` runs real exports via a `task` callable and updates `progress` / `current_frame` / `total_frames`
- `POST /api/export` enqueues a job; `GET /api/export/status/{id}` returns live queue state (`queued` → `running` → `completed`/`failed`); `GET /api/export/download/{id}.{ext}` serves the file
- MP4, MOV (ffmpeg), and Live Photo (HEIC + MOV + manifest, zipped) export verified end-to-end
- `routes.py` no longer uses `BackgroundTasks`; `BackgroundTasks` import removed
- Fixed `init_job_queue` to mutate the module singleton (was rebinding a new instance that routes imported by value — jobs were stuck queued with no workers)
- Fixed `LivePhotoExporter.create_ios_import_package` to exclude the zip it writes into the same dir (was recursively self-including and ballooning)

### Static / SPA serving
- `main.py` mounts `webapp/dist` at `/` via `SPAStaticFiles` (StaticFiles subclass) with React-router fallback to `index.html`; `/api`, `/health`, `/exports` still take precedence

### Webapp (React)
- **Discover** — cycling hero (4 gen/preset combos), generator grid, featured preset grid with live still thumbs
- **Studio** — generator rail (6 gens incl. `flowing_curve` marked "New"; `l_system`/`color_cycle` scaffolded), schema-driven forms, debounced canvas preview, output controls (device/fps/duration/cmap/seed), ExportPanel with progress + download
- **Library** — export job cards (live `useSyncExternalStore`), poster thumbs, 5-step iPhone install guide
- Local mocks mirror the FastAPI contract 1:1; `lib/api.ts` provides a typed client with `USE_API` / `API_BASE` flags (`VITE_USE_API`, `VITE_API_BASE`) to switch the export flow to the real backend

## Known Issues

1. **L-System & Color Cycle are scaffolded** — registered but `generate_frame` doesn't render real output
2. **Webapp preview still uses local canvas** — doesn't consume the backend MJPEG stream yet (MJPEG wired in `PreviewCanvas` only in API mode is pending)
3. **`preview/websocket.py` is a stub** — `api/websocket.py` is implemented; the preview-level WS is not
4. **Numba `reflected set` deprecation** — `_gol_step` uses Python sets which numba plans to deprecate (migration to `numba.typed.Set` pending)
5. **Webapp data layer still mocked** — generator/preset listings fetched from the API are mapped in `lib/api.ts` but the UI uses local `data.ts`

## TODO / Next Steps

### High Priority
- [ ] **Implement L-System generator** — turtle-based fractal plant rendering with grow/rotate/wind animations
- [ ] **Implement Color Cycle generator** — procedural plasma/fire/aurora patterns
- [x] **Export job queue + status + download** — real queue, progress tracking, file download (done this session)
- [x] **Live Photo export verified** — HEIC + MOV + zip bundle returned correctly
- [ ] **Auto-apply presets across generators** — clearing a preset when switching generators
- [ ] **"Time spiral" animation for Julia** — spiral path for `c` (varying radius + angle over time)

### Medium Priority
- [ ] **Wire webapp studio preview to backend MJPEG** — stream `/api/preview/stream` behind `USE_API`
- [ ] **Wire webapp generators/presets from the API** — replace local `data.ts` with `lib/api.ts` responses
- [ ] **WebSocket preview** — lower latency than MJPEG, bidirectional param updates
- [ ] **Numba reflected set fix** — migrate `_gol_step` to `numba.typed.Set`
- [ ] **Test coverage additions** — preset loading, more API edge cases
- [ ] **Docker optimization** — multi-stage build, smaller image
- [ ] **Better Streamlit error messages** — when API returns 4xx
- [ ] **Parameter range validation feedback** — UI when params exceed schema bounds

### Low Priority
- [ ] **Keyboard shortcut** — space to play/pause preview
- [ ] **Comparison view** — side-by-side before/after for param changes
- [x] **Export history** — Library page lists past exports with re-download (done in webapp)
- [ ] **iOS Shortcut** — auto-apply exported Live Photo as wallpaper
- [ ] **Analytics** — count exports, popular presets

## Bugs Fixed in Previous Session

- Julia/Mandelbrot preview returning 400: `JuliaParams` & `GameOfLifeParams` missing fields the param schema defined (`animation_mode`, `spin_radius`, `rule_birth`, `trail_decay`, etc.)
- Preview URL passing individual params instead of JSON `params` string
- `use_container_width` deprecated → `width='stretch'`
- `GameOfLifeGenerator.__init__()` missing `super().__init__()` call
- `@dataclass` missing on all `*Params` subclasses
- Extra blank lines after `@register_generator` decorators

## Bugs Fixed This Session

- **Job queue never ran exports**: `init_job_queue` reassigned a new `JobQueue` instance, but `routes.py` had imported the original singleton by value, so jobs were enqueued onto a queue with no workers → now mutates the shared singleton
- **Live Photo zip runaway growth**: `create_ios_import_package` zipped `output_dir` while writing the zip *into* it, recursively including itself (grew toward 2 GB) → exclude the output zip from the scan
- **Stale export stub**: `/api/export/status` always returned `completed`; now reads the real job queue
- **Clean lint/typecheck**: fixed pre-existing ruff errors in tests (dead imports, sorted imports) and mypy errors (numba `prange` iteration, OpenCV `VideoWriter_fourcc`, `ffmpeg`/`pillow-heif` stubs, a `no-any-return` in streamlit_app); `just check` is fully green
- **Test client dependency**: added `httpx` to dev deps for `fastapi.testclient`
- **Sample media hygiene**: `vendor-livp/` (sample HEIC/MOV) removed and explicitly gitignored

## Session Notes — Webapp polish & real-API wiring

- **Light/dark theme**: `lib/theme.ts` persists a `fw.theme` key and applies `data-theme` on `<html>`; `[data-theme='light']` overrides the oklch tokens in `app.css`. Toggle lives in the topbar (`.theme-toggle`).
- **Sticky Studio layout**: `.studio` is now a fixed `height: calc(100dvh - topbar)` grid with each column (params / canvas / rail) scrolling independently, so long param sets stay in view. Responsive breakpoints reset to normal page scroll.
- **FE talks to the real backend by default**: `USE_API` in `lib/api.ts` is now `!== '0'` (was `=== '1'`, defaulting to mocks). A normal `webapp-build` now drives real encoding same-origin. Set `VITE_USE_API=0` for standalone mock FE dev. `just webapp-dev` runs Vite with `VITE_API_BASE=http://localhost:8000` so Studio talks to a local `just api`.
- **Verified**: built SPA served by FastAPI runs a true encoded export (HEIC + MOV + zip for Live Photo); status poll + download endpoint return the real file (`CONTENT-DISPOSITION: attachment`).
- **Generate button re-arm**: ExportPanel `disabled` now only during an in-flight job (`running && !done`), so re-exporting after a finished/failed job works without a reload.
- **Switch control fix**: `.switch i` (the pill) is now `pointer-events:none`, so clicks on the visible toggle reach the hidden checkbox — the `Adaptive timing` switch can now be toggled off.
- **`prescribed` → `uzumaki`**: webapp mode enum, `uzumaki` preset, JS `curveXY` branch, and docs (scripts/README, README alt, STATUS) aligned to `uzumaki`, matching the backend and `scripts/flowing_curve_demo.py`.

## Session Notes — Backend logging, log-level config & export 400/encode fixes

- **Structured logging**: added `src/fluxwall/core/logging.py` (`configure_logging()` + `get_logger()`). `main.py` configures it at import, adds a global 500 exception handler (`logger.exception`, `# noqa: LOG004`) and startup/shutdown logs. `api/routes.py` and `core/job_queue.py` now log export lifecycle (accept/reject/status/download, enqueue/start/fail/finish) — params at DEBUG, warnings at WARNING, failures with tracebacks.
- **Log level configurable**: `Settings.log_level` accepts `LOG_LEVEL` / `LOGGER_LEVEL` / `FLUXWALL_LOG_LEVEL` via `validation_alias=AliasChoices(...)` + `populate_by_name`. Run debug with `LOGGER_LEVEL=DEBUG uvicorn fluxwall.main:app`.
- **POST /api/export 400 fixed**: webapp sends `adaptive` / `adaptive_strength` for `flowing_curve`, but `FlowingCurveParams` didn't declare them → validation rejected ("unexpected keyword argument 'adaptive'"). Added both fields to `src/fluxwall/core/models.py`; the request now accepts and exports.
- **ffmpeg broken-pipe (encode) fixed**: the deeper bug — libx264 + `yuv420p` require **even** dimensions, but iPhone 15 Pro is 1179×2556 (odd width), so the encoder failed to open and stdin writes got EPIPE ("Conversion failed!"). `core/exporters/video.py` `export_video` now rounds encode + frame size down to even dims (1178×2556).
- **Verified end-to-end**: restart API, `POST /api/export` (flowing_curve, 15_pro MOV) → 200, job `completed`, `output.mov` at 1179×2556/15 frames; `just check` + 36 tests green.