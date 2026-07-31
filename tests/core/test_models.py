"""Tests for FluxWall core models."""

from __future__ import annotations

from fluxwall.core.models import GeneratorParams, ExportOptions, ExportFormat, ColorMap, GeneratorType, iPhoneModel


def test_generator_params_defaults():
    params = GeneratorParams(width=1170, height=2532, fps=30, duration_sec=4.0)
    assert params.width == 1170
    assert params.height == 2532
    assert params.fps == 30
    assert params.duration_sec == 4.0
    assert params.colormap == "magma"


def test_generator_params_seed_nullable():
    params = GeneratorParams(width=100, height=100, fps=30, duration_sec=1.0, seed=None)
    assert params.seed is None
    params_with_seed = GeneratorParams(width=100, height=100, fps=30, duration_sec=1.0, seed=42)
    assert params_with_seed.seed == 42


def test_export_options_defaults():
    opts = ExportOptions()
    assert opts.format == ExportFormat.MP4
    assert opts.fps == 30
    assert opts.duration_sec == 3.0
    assert opts.iphone_model == iPhoneModel.IPHONE_15_PRO_MAX


def test_export_options_custom():
    opts = ExportOptions(
        format=ExportFormat.LIVE_PHOTO,
        fps=60,
        duration_sec=10.0,
        iphone_model=iPhoneModel.IPHONE_14_PRO,
    )
    assert opts.format == ExportFormat.LIVE_PHOTO
    assert opts.fps == 60
    assert opts.duration_sec == 10.0
    assert opts.iphone_model == iPhoneModel.IPHONE_14_PRO


def test_iphone_model_resolution():
    assert iPhoneModel.IPHONE_15_PRO_MAX.resolution == (1290, 2796)
    assert iPhoneModel.IPHONE_15_PRO.resolution == (1179, 2556)
    assert iPhoneModel.IPHONE_14_PRO.resolution == (1170, 2532)
    assert iPhoneModel.IPHONE_SE.resolution == (750, 1334)


def test_colormap_values():
    values = [cm.value for cm in ColorMap]
    assert "magma" in values
    assert "viridis" in values
    assert "plasma" in values


def test_generator_type_values():
    assert GeneratorType.GAME_OF_LIFE.value == "game_of_life"
    assert GeneratorType.MANDELBROT.value == "mandelbrot"
    assert GeneratorType.JULIA.value == "julia"
