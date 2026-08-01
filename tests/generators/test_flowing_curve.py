"""Tests for the Flowing Curve generator."""

from __future__ import annotations

import numpy as np
import pytest

from fluxwall.core.models import FlowingCurveParams, GeneratorParams
from fluxwall.generators import discover_generators
from fluxwall.generators.flowing_curve import SUPPORTED_MODES
from fluxwall.generators.registry import registry


@pytest.fixture(scope='module', autouse=True)
def discover() -> None:
    discover_generators()


ALL_MODES = list(SUPPORTED_MODES)


@pytest.fixture
def base_params() -> GeneratorParams:
    return GeneratorParams(width=117, height=253, fps=10, duration_sec=1.0)


@pytest.mark.parametrize('mode', ALL_MODES)
def test_all_modes_return_valid_frame(mode: str, base_params: GeneratorParams) -> None:
    params = FlowingCurveParams(mode=mode, width=base_params.width, height=base_params.height)
    gen = registry.get('flowing_curve')
    assert gen is not None

    frame = gen.generate_frame(0, params)

    assert isinstance(frame, np.ndarray)
    assert frame.dtype == np.uint8
    assert frame.shape == (253, 117, 3)


def test_uzumaki_registered() -> None:
    gen = registry.get('flowing_curve')
    assert gen is not None
    assert gen.name == 'flowing_curve'
    assert gen.display_name == 'Flowing Curve'
    assert 'uzumaki' in gen.presets
    assert 'golden_spiral' in gen.presets


def test_uzumaki_supersample_evolution() -> None:
    params = FlowingCurveParams(
        mode='uzumaki',
        width=100,
        height=100,
        fps=10,
        duration_sec=1.0,
        supersample=4,
    )
    gen = registry.get('flowing_curve')
    assert gen is not None

    frames = list(gen.generate_frames(params))

    assert len(frames) == 10
    assert all(f.shape == (100, 100, 3) for f in frames)
    assert all(f.dtype == np.uint8 for f in frames)


def test_fixed_limits_mode() -> None:
    params = FlowingCurveParams(
        mode='sin',
        width=80,
        height=120,
        fps=5,
        duration_sec=1.0,
        auto_limits=False,
    )
    gen = registry.get('flowing_curve')
    assert gen is not None

    frame = gen.generate_frame(2, params)

    assert frame.shape == (120, 80, 3)
    assert frame.dtype == np.uint8


def test_unknown_mode_raises() -> None:
    params = FlowingCurveParams(mode='not_a_mode', width=80, height=80)
    gen = registry.get('flowing_curve')
    assert gen is not None

    with pytest.raises(ValueError, match='Unknown mode'):
        gen.generate_frame(0, params)


def test_validate_params() -> None:
    gen = registry.get('flowing_curve')
    assert gen is not None

    valid = gen.validate_params({'mode': 'uzumaki', 'supersample': 6})
    assert valid is not None
    assert valid.mode == 'uzumaki'
    assert valid.supersample == 6
