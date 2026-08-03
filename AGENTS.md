<!-- headroom:rtk-instructions -->
# RTK (Rust Token Killer) - Token-Optimized Commands

When running shell commands, **always prefix with `rtk`**. This reduces context
usage by 60-90% with zero behavior change. If rtk has no filter for a command,
it passes through unchanged — so it is always safe to use.

## Key Commands
```bash
# Git (59-80% savings)
rtk git status          rtk git diff            rtk git log

# Files & Search (60-75% savings)
rtk ls <path>           rtk read <file>         rtk grep <pattern>
rtk find <pattern>      rtk diff <file>

# Test (90-99% savings) — shows failures only
rtk pytest tests/       rtk cargo test          rtk test <cmd>

# Build & Lint (80-90% savings) — shows errors only
rtk tsc                 rtk lint                rtk cargo build
rtk prettier --check    rtk mypy                rtk ruff check

# Analysis (70-90% savings)
rtk err <cmd>           rtk log <file>          rtk json <file>
rtk summary <cmd>       rtk deps                rtk env

# GitHub (26-87% savings)
rtk gh pr view <n>      rtk gh run list         rtk gh issue list

# Infrastructure (85% savings)
rtk docker ps           rtk kubectl get         rtk docker logs <c>

# Package managers (70-90% savings)
rtk pip list            rtk pnpm install        rtk npm run <script>
```

## Rules
- In command chains, prefix each segment: `rtk git add . && rtk git commit -m "msg"`
- For debugging, use raw command without rtk prefix
- `rtk proxy <cmd>` runs command without filtering but tracks usage
<!-- /headroom:rtk-instructions -->

---

# FluxWall Project Conventions

## Git Workflow (MANDATORY)
- **`main` branch** = deployment branch (Railway auto-deploys from main)
- **Never commit directly to `main`**
- All work happens on feature branches: `feature/<name>`, `fix/<name>`, `chore/<name>`
- Create PR → review → merge to `main` (triggers Railway deploy)
- Branch naming: `feature/game-of-life-generator`, `fix/heic-export-fallback`, `chore/update-deps`

## Code Style
- **Python 3.12+** with type hints everywhere
- **Ruff** for linting + formatting (`ruff check`, `ruff format`)
- **mypy** strict mode for type checking
- **NumPy** style docstrings for public APIs
- **Pydantic v2** for all data models/validation

## Architecture Principles
- **Generator Plugin System**: New generators = new class in `generators/`, auto-registered
- **Async-first**: FastAPI async endpoints, background jobs for exports
- **Streaming Preview**: MJPEG over HTTP (MVP), WebSocket binary (pending)
- **Live Photo Export**: HEIC + MOV paired export with manifest (native HEIC first, fallback to paired files)

## Project Structure
The repo is a monorepo split into `backend/` (FastAPI + Streamlit) and `frontend/` (React SPA).
```
backend/
├── src/fluxwall/
│   ├── main.py                 # FastAPI app entry (also serves frontend/dist at /)
│   ├── streamlit_app.py        # Streamlit UI entry
│   ├── config.py               # Settings (pydantic-settings)
│   ├── core/
│   │   ├── models.py           # Pydantic schemas (params, presets, jobs)
│   │   ├── presets.py          # Built-in preset registry
│   │   ├── exporters/
│   │   │   ├── video.py        # MP4/MOV via ffmpeg-python
│   │   │   ├── heic.py         # HEIC still via pillow-heif
│   │   │   └── live_photo.py   # Live Photo bundler (HEIC+MOV+manifest)
│   │   └── job_queue.py        # Async job management
│   ├── generators/
│   │   ├── base.py             # Abstract Generator base class
│   │   ├── registry.py         # Generator plugin registry
│   │   ├── game_of_life.py
│   │   ├── mandelbrot.py
│   │   ├── julia.py
│   │   ├── l_system.py
│   │   └── color_cycle.py
│   ├── api/
│   │   ├── routes.py           # REST endpoints
│   │   ├── websocket.py        # Real-time frame streaming (pending)
│   │   └── schemas.py          # API request/response models
│   ├── preview/
│   │   ├── mjpeg.py            # MJPEG over HTTP endpoint
│   │   └── websocket.py        # Binary WebSocket frame streaming (pending)
│   └── utils/
│       ├── colors.py           # Colormaps, palettes
│       ├── math.py             # Numba-accelerated kernels
│       └── video.py            # Frame utilities
├── presets/                    # Generator preset JSON
├── assets/                     # Image assets/colormaps
├── tests/                      # Mirror of src/ structure
└── pyproject.toml              # uv project

frontend/                       # React 19 + Vite + TS SPA
├── src/
└── package.json
```

## Generator Interface
```python
class Generator(ABC):
    name: str = "base"
    display_name: str = "Base Generator"
    description: str = ""
    param_schema: dict = {}  # JSON Schema for parameter validation
    presets: dict[str, dict] = {}  # name -> param overrides

    @abstractmethod
    def generate_frame(self, frame_idx: int, params: GeneratorParams) -> NDArray[np.uint8]:
        """Generate a single RGB frame (H, W, 3)"""
        pass

    def generate_frames(self, params: GeneratorParams) -> Iterator[NDArray[np.uint8]]:
        """Yield frames for full duration"""
        total_frames = int(params.fps * params.duration_sec)
        for i in range(total_frames):
            yield self.generate_frame(i, params)
```

## Adding a New Generator
1. Create `backend/src/fluxwall/generators/<name>.py` with class extending `Generator`
2. Register in `backend/src/fluxwall/generators/registry.py` (auto-discovery via `__init__.py`)
3. Add preset JSON files in `backend/presets/<name>/`
4. No other changes needed — API/UI auto-discovers

## Export Formats
| Format | Use Case | Implementation |
|--------|----------|----------------|
| MP4 | General video | `ffmpeg-python` H.264/yuv420p |
| MOV | iOS compatible | `ffmpeg-python` H.264/yuv420p |
| HEIC | iOS still (Live Photo) | `pillow-heif` (native attempt) |
| Live Photo | iOS lock screen | HEIC + MOV + manifest.json |

## iPhone Resolutions (Portrait)
| Model | Width × Height |
|-------|----------------|
| 15/16 Pro Max | 1290 × 2796 |
| 15/16 Pro | 1179 × 2556 |
| 14/13/12 Pro | 1170 × 2532 |
| SE / 8 | 750 × 1334 |

## Preview Strategy
- **MVP**: MJPEG over HTTP (`GET /api/preview/stream?job_id=...`) → `<img src="...">` in Streamlit
- **Pending**: Binary WebSocket (`WS /ws/preview/{job_id}`) for lower latency, bidirectional param updates

## Justfile Commands
```bash
just dev          # Run dev server (API + Streamlit)
just api          # FastAPI only
just ui           # Streamlit only
just check        # fmt + lint + typecheck
just test         # pytest
just docker-build # Build image
just deploy       # Railway deploy (from main branch only)
```

## Testing
- Unit tests in `backend/tests/` mirroring `backend/src/` structure
- `pytest -v` for verbose, `pytest --cov=fluxwall` for coverage
- Generator tests: verify frame output shape, dtype, parameter validation

## Deployment
- Railway connected to GitHub repo
- Auto-deploy on merge to `main`
- Staging/production environments via Railway environments
- Health check: `GET /health`