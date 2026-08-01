"""Pydantic models for FluxWall generators, presets, and exports."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field, field_validator


class ColorMap(StrEnum):
    """Available matplotlib colormaps."""

    MAGMA = 'magma'
    VIRIDIS = 'viridis'
    PLASMA = 'plasma'
    INFERNO = 'inferno'
    CIVIDIS = 'cividis'
    TWILIGHT = 'twilight'
    TURBO = 'turbo'
    HOT = 'hot'
    COOL = 'cool'
    SPRING = 'spring'
    SUMMER = 'summer'
    AUTUMN = 'autumn'
    WINTER = 'winter'
    FIRE = 'fire'
    PLASMA_R = 'plasma_r'
    MAGMA_R = 'magma_r'


class GeneratorType(StrEnum):
    """Supported generator types."""

    GAME_OF_LIFE = 'game_of_life'
    MANDELBROT = 'mandelbrot'
    JULIA = 'julia'
    L_SYSTEM = 'l_system'
    COLOR_CYCLE = 'color_cycle'
    FLOWING_CURVE = 'flowing_curve'


class ExportFormat(StrEnum):
    """Export output formats."""

    MP4 = 'mp4'
    MOV = 'mov'
    LIVE_PHOTO = 'live_photo'


class iPhoneModel(StrEnum):
    """Supported iPhone models for resolution targeting."""

    IPHONE_15_PRO_MAX = '15_pro_max'
    IPHONE_15_PRO = '15_pro'
    IPHONE_14_PRO = '14_pro'
    IPHONE_SE = 'se'

    @property
    def resolution(self) -> tuple[int, int]:
        return IPHONE_RESOLUTIONS[self]


IPHONE_RESOLUTIONS: dict[iPhoneModel, tuple[int, int]] = {
    iPhoneModel.IPHONE_15_PRO_MAX: (1290, 2796),
    iPhoneModel.IPHONE_15_PRO: (1179, 2556),
    iPhoneModel.IPHONE_14_PRO: (1170, 2532),
    iPhoneModel.IPHONE_SE: (750, 1334),
}


@dataclass
class GeneratorParams:
    """Base parameters shared by all generators."""

    width: int = 1290
    height: int = 2796
    fps: int = 30
    duration_sec: float = 3.0
    colormap: str = 'magma'
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.seed is not None:
            np.random.seed(self.seed)

    @property
    def total_frames(self) -> int:
        return int(self.fps * self.duration_sec)


@dataclass
class GameOfLifeParams(GeneratorParams):
    """Parameters for Conway's Game of Life generator."""

    grid_width: int = 120
    grid_height: int = 240
    initial_pattern: str = 'random'
    rule_birth: str = '3'
    rule_survive: str = '23'
    wrap_edges: bool = True
    trail_length: int = 5
    trail_decay: float = 0.95
    trail_colormap: str = 'plasma'
    color_live: str = '#ffffff'
    color_dead: str = '#000000'
    pattern_scale: float = 1.0


@dataclass
class MandelbrotParams(GeneratorParams):
    """Parameters for Mandelbrot Set generator."""

    center_x: float = -0.5
    center_y: float = 0.0
    zoom: float = 1.0
    max_iter: int = 1000
    zoom_factor_per_frame: float = 1.02
    color_cycle_speed: float = 0.0
    smooth_coloring: bool = True


@dataclass
class JuliaParams(GeneratorParams):
    """Parameters for Julia Set generator."""

    c_real: float = -0.7269
    c_imag: float = 0.1889
    zoom: float = 1.0
    max_iter: int = 500
    animation_mode: str = 'spin'
    spin_radius: float = 0.7885
    spin_speed: float = 1.0
    zoom_factor_per_frame: float = 1.02
    rotation_speed: float = 0.0
    rotation_radius: float = 0.7885
    color_cycle_speed: float = 0.0
    smooth_coloring: bool = True


@dataclass
class LSystemParams(GeneratorParams):
    """Parameters for L-System generator."""

    axiom: str = 'X'
    rules: dict[str, str] = Field(default_factory=lambda: {'X': 'F+[[X]-X]-F[-FX]+X', 'F': 'FF'})
    angle: float = 25.0
    iterations: int = 6
    line_width: float = 2.0
    color_by_depth: bool = True
    color_scheme: str = 'plant'  # plant, rainbow, fire, mono
    animation_mode: str = 'grow'  # grow, rotate, wind
    wind_strength: float = 0.0


@dataclass
class ColorCycleParams(GeneratorParams):
    """Parameters for Color Cycling generator."""

    pattern_type: str = 'plasma'  # plasma, fire, aurora, reaction_diffusion, flow_field
    frequency: float = 0.01
    speed: float = 0.1
    turbulence: float = 0.0
    octaves: int = 4
    persistence: float = 0.5


@dataclass
class FlowingCurveParams(GeneratorParams):
    """Parameters for the Flowing Curve generator.

    Modes:
    - ``uzumaki``: the signature spirograph-style spiral (hardcoded 2000-point
      recurrence in the original demo, generalized to ``steps``).
    - ``linear``/``log``/``sqrt``/``sin``/``golden``/``poly``: generic
      complex-plane recurrences whose phase sweeps with time.
    """

    mode: str = 'uzumaki'  # uzumaki, linear, log, sqrt, sin, golden, poly
    steps: int = 2000
    step_size: float = 0.008
    omega: float = 0.15
    exp: float = 0.5
    mod_freq: float = 0.05
    mod_amp: float = 0.5
    line_width: float = 1.0
    alpha: float = 0.85
    t_start: float = 0.0
    t_end: float = 1.0
    supersample: int = 1
    blur_decay: float = 0.55
    auto_limits: bool = True


class Preset(BaseModel):
    """A saved preset configuration for a generator."""

    id: str
    generator: GeneratorType
    name: str
    description: str = ''
    params: dict[str, Any]
    export: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    version: int = 1


class ExportOptions(BaseModel):
    """Options for video/Live Photo export."""

    format: ExportFormat = ExportFormat.MP4
    iphone_model: iPhoneModel = iPhoneModel.IPHONE_15_PRO_MAX
    fps: int = 30
    duration_sec: float = 3.0
    quality: int = 90

    @field_validator('duration_sec')
    @classmethod
    def validate_duration(cls, v: float) -> float:
        if v > 30.0:
            raise ValueError('Duration cannot exceed 30 seconds for Live Photo')
        return v


class ExportJob(BaseModel):
    """An export job tracking async generation."""

    id: UUID = Field(default_factory=uuid4)
    generator: GeneratorType
    params: dict[str, Any]
    options: ExportOptions
    status: Literal['pending', 'running', 'completed', 'failed'] = 'pending'
    progress: float = 0.0
    current_frame: int = 0
    total_frames: int = 0
    output_path: str | None = None
    error: str | None = None
    created_at: float = Field(default_factory=lambda: __import__('time').time())
    started_at: float | None = None
    completed_at: float | None = None


class PreviewJob(BaseModel):
    """A live preview session."""

    id: UUID = Field(default_factory=uuid4)
    generator: GeneratorType
    params: dict[str, Any]
    target_fps: int = 15
    status: Literal['starting', 'running', 'stopped'] = 'starting'
    created_at: float = Field(default_factory=lambda: __import__('time').time())


# Type alias for frame arrays
FrameArray = NDArray[np.uint8]  # Shape: (H, W, 3) RGB
