"""Abstract base class for all parametric generators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from fluxwall.core.models import FrameArray, GeneratorParams


@dataclass
class GeneratorInfo:
    """Metadata for generator registration."""

    name: str
    display_name: str
    description: str
    param_schema: dict[str, Any]
    presets: dict[str, dict[str, Any]]


class Generator(ABC):
    """Abstract base class for all parametric wallpaper generators."""

    # Class-level metadata (override in subclasses)
    name: str = 'base'
    display_name: str = 'Base Generator'
    description: str = ''
    param_schema: dict[str, Any] = {}
    presets: dict[str, dict[str, Any]] = {}

    def __init__(self) -> None:
        self._info = GeneratorInfo(
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            param_schema=self.param_schema,
            presets=self.presets,
        )

    @property
    def info(self) -> GeneratorInfo:
        return self._info

    @abstractmethod
    def generate_frame(self, frame_idx: int, params: GeneratorParams) -> FrameArray:
        """Generate a single RGB frame (H, W, 3).

        Args:
            frame_idx: Zero-based frame index
            params: Generator parameters

        Returns:
            RGB frame as uint8 array of shape (height, width, 3)
        """
        pass

    def generate_frames(self, params: GeneratorParams) -> Iterator[FrameArray]:
        """Yield frames for the full duration.

        Args:
            params: Generator parameters

        Yields:
            RGB frames as uint8 arrays
        """
        total_frames = params.total_frames
        for i in range(total_frames):
            yield self.generate_frame(i, params)

    def get_default_params(self) -> GeneratorParams:
        """Return default parameters for this generator."""
        return GeneratorParams()

    def validate_params(self, params: dict[str, Any]) -> GeneratorParams:
        """Validate and convert params dict to typed params object.

        Override in subclasses for specific param types.
        """
        return GeneratorParams(**params)


class FrameBuffer:
    """Utility for managing frame buffers efficiently."""

    def __init__(self, height: int, width: int, dtype: type = np.uint8) -> None:
        self.height = height
        self.width = width
        self.dtype = dtype
        self._buffer: NDArray[np.uint8] = np.zeros((height, width, 3), dtype=dtype)

    @property
    def array(self) -> FrameArray:
        return self._buffer

    def clear(self, color: tuple[int, int, int] = (0, 0, 0)) -> None:
        self._buffer[:] = color

    def set_region(self, y: int, x: int, h: int, w: int, color: tuple[int, int, int]) -> None:
        self._buffer[y : y + h, x : x + w] = color
