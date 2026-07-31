# FluxWall

<img src="output/prescribed_samples.png" alt="FluxWall prescribed samples" width="600" />

**Parametric iOS Live Wallpaper Generator** — FluxWall turns code-driven, generative art into iOS live wallpapers. It pairs a FastAPI backend with a Streamlit UI to generate, preview, and export Live Photos (HEIC + MOV) from a plugin system of procedural generators.

## Features

- **Generator Plugin System** — drop a new class in `generators/` and it's auto-registered for API and UI
- **Procedural generators** — Game of Life, Mandelbrot, Julia, L-Systems, and color cycle
- **Async-first** — FastAPI async endpoints with background jobs for exports
- **Streaming preview** — MJPEG over HTTP for live `<img>` previews in Streamlit
- **Live Photo export** — native HEIC stills with MOV paired export and manifest (native HEIC first, fallback to paired files)
- **iPhone-optimized** — presets for iPhone 15/16 Pro Max, 15/16 Pro, 14/13/12 Pro, and SE/8 resolutions

## Architecture

```
src/fluxwall/
├── main.py                 # FastAPI app entry
├── streamlit_app.py        # Streamlit UI entry
├── config.py               # Settings (pydantic-settings)
├── core/
│   ├── models.py           # Pydantic schemas (params, presets, jobs)
│   ├── presets.py          # Built-in preset registry
│   ├── exporters/
│   │   ├── video.py        # MP4/MOV via ffmpeg-python
│   │   ├── heic.py         # HEIC still via pillow-heif
│   │   └── live_photo.py   # Live Photo bundler (HEIC+MOV+manifest)
│   └── job_queue.py        # Async job management
├── generators/
│   ├── base.py             # Abstract Generator base class
│   ├── registry.py         # Generator plugin registry
│   ├── game_of_life.py
│   ├── mandelbrot.py
│   ├── julia.py
│   ├── l_system.py
│   └── color_cycle.py
├── api/
│   ├── routes.py           # REST endpoints
│   ├── websocket.py        # Real-time frame streaming (pending)
│   └── schemas.py          # API request/response models
├── preview/
│   ├── mjpeg.py            # MJPEG over HTTP endpoint
│   └── websocket.py        # Binary WebSocket frame streaming (pending)
└── utils/
    ├── colors.py           # Colormaps, palettes
    ├── math.py             # Numba-accelerated kernels
    └── video.py            # Frame utilities
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

## Export Formats

| Format | Use Case | Implementation |
|--------|----------|----------------|
| MP4 | General video | `ffmpeg-python` H.264/yuv420p |
| MOV | iOS compatible | `ffmpeg-python` H.264/yuv420p |
| HEIC | iOS still (Live Photo) | `pillow-heif` (native attempt) |
| Live Photo | iOS lock screen | HEIC + MOV + manifest.json |

## Quickstart

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

- Unit tests in `tests/` mirroring `src/` structure
- `pytest -v` for verbose, `pytest --cov=fluxwall` for coverage
- Generator tests verify frame output shape, dtype, and parameter validation

## Deployment

- Railway connected to GitHub repo, auto-deploys on merge to `main`
- Staging/production environments via Railway environments
- Health check: `GET /health`
