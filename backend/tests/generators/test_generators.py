"""Tests for generators - frame output validation."""

from __future__ import annotations

import numpy as np
import pytest

from fluxwall.core.models import GeneratorParams
from fluxwall.generators import discover_generators
from fluxwall.generators.registry import registry


@pytest.fixture(scope='session', autouse=True)
def discover():
    discover_generators()


@pytest.fixture
def base_params() -> GeneratorParams:
    return GeneratorParams(width=117, height=253, fps=10, duration_sec=1.0)


@pytest.mark.parametrize('gen_name', ['game_of_life', 'mandelbrot', 'julia'])
def test_generator_returns_frame(gen_name: str, base_params: GeneratorParams):
    gen = registry.get(gen_name)
    assert gen is not None, f"Generator '{gen_name}' not registered"

    frame = gen.generate_frame(0, base_params)

    assert isinstance(frame, np.ndarray)
    assert frame.dtype == np.uint8
    assert frame.shape == (253, 117, 3)  # (H, W, 3)


def test_game_of_life_frame_evolution(base_params: GeneratorParams):
    gen = registry.get('game_of_life')
    assert gen is not None

    frame0 = gen.generate_frame(0, base_params)
    frame1 = gen.generate_frame(1, base_params)

    assert frame0.shape == frame1.shape
    assert frame0.dtype == frame1.dtype


def test_mandelbrot_zoom_evolution():
    params = GeneratorParams(width=100, height=100, fps=10, duration_sec=1.0)
    gen = registry.get('mandelbrot')
    assert gen is not None

    frames = list(gen.generate_frames(params))
    assert len(frames) == 10
    assert all(f.shape == (100, 100, 3) for f in frames)


def test_julia_spin_evolution():
    params = GeneratorParams(width=100, height=100, fps=10, duration_sec=2.0)
    gen = registry.get('julia')
    assert gen is not None

    frames = list(gen.generate_frames(params))
    assert len(frames) == 20
    assert all(f.dtype == np.uint8 for f in frames)


def test_generator_name_and_presets():
    for gen_name in ['game_of_life', 'mandelbrot', 'julia']:
        gen = registry.get(gen_name)
        assert gen is not None
        assert gen.name == gen_name
        assert gen.display_name
        assert gen.description
        assert gen.param_schema
        assert 'properties' in gen.param_schema


def test_generator_validate_params():
    gen = registry.get('mandelbrot')
    assert gen is not None

    valid = gen.validate_params({'center_x': -0.5, 'center_y': 0.0})
    assert valid is not None
    assert valid.center_x == -0.5

    # Dataclass params don't validate types (use Pydantic for strict validation)
    invalid = gen.validate_params({'center_x': 'not_a_number'})
    assert invalid.center_x == 'not_a_number'
