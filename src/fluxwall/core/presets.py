"""Preset registry and loading."""

from __future__ import annotations

import json
from pathlib import Path

from fluxwall.core.models import GeneratorType, Preset


class PresetRegistry:
    """Registry for managing generator presets."""

    def __init__(self, presets_dir: Path | None = None):
        self.presets_dir = presets_dir or Path(__file__).parent.parent.parent.parent / 'presets'
        self._presets: dict[str, Preset] = {}
        self._loaded = False

    def load_all(self) -> None:
        """Load all presets from directory."""
        if not self.presets_dir.exists():
            return

        for gen_dir in self.presets_dir.iterdir():
            if not gen_dir.is_dir():
                continue

            for preset_file in gen_dir.glob('*.json'):
                try:
                    with preset_file.open() as f:
                        data = json.load(f)

                    preset = Preset(**data)
                    self._presets[preset.id] = preset

                except Exception:
                    pass

        self._loaded = True

    def get(self, preset_id: str) -> Preset | None:
        """Get preset by ID."""
        if not self._loaded:
            self.load_all()
        return self._presets.get(preset_id)

    def get_all(self) -> list[Preset]:
        """Get all presets."""
        if not self._loaded:
            self.load_all()
        return list(self._presets.values())

    def get_by_generator(self, generator: GeneratorType) -> list[Preset]:
        """Get presets for a specific generator."""
        if not self._loaded:
            self.load_all()
        return [p for p in self._presets.values() if p.generator == generator]

    def register(self, preset: Preset) -> None:
        """Register a preset programmatically."""
        self._presets[preset.id] = preset


# Global registry
preset_registry = PresetRegistry()


def load_presets() -> None:
    """Load all presets into registry."""
    preset_registry.load_all()


# Preset directory structure:
# presets/
#   game_of_life/
#     gosper_gun.json
#     glider_swarm.json
#     random_soup.json
#   mandelbrot/
#     classic.json
#     seahorse_valley.json
#     elephant_valley.json
#   julia/
#     douady_rabbit.json
#     dendrite.json
#     spiral.json
#   l_system/
#     fractal_tree.json
#     barnsley_fern.json
#   color_cycle/
#     plasma.json
#     fire.json
