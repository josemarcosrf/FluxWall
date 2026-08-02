"""Generator plugin registry with auto-discovery."""

from __future__ import annotations

from fluxwall.generators.base import Generator, GeneratorInfo


class GeneratorRegistry:
    """Registry for managing generator plugins."""

    def __init__(self) -> None:
        self._generators: dict[str, Generator] = {}
        self._infos: dict[str, GeneratorInfo] = {}

    def register(self, generator: Generator) -> None:
        """Register a generator instance."""
        if generator.name in self._generators:
            raise ValueError(f"Generator '{generator.name}' already registered")
        self._generators[generator.name] = generator
        self._infos[generator.name] = generator.info

    def unregister(self, name: str) -> None:
        """Unregister a generator."""
        self._generators.pop(name, None)
        self._infos.pop(name, None)

    def get(self, name: str) -> Generator | None:
        """Get a generator by name."""
        return self._generators.get(name)

    def get_info(self, name: str) -> GeneratorInfo | None:
        """Get generator metadata by name."""
        return self._infos.get(name)

    def get_all(self) -> list[GeneratorInfo]:
        """List all registered generators."""
        return list(self._infos.values())

    def list_names(self) -> list[str]:
        """List all registered generator names."""
        return list(self._generators.keys())

    def has(self, name: str) -> bool:
        """Check if a generator is registered."""
        return name in self._generators


# Global registry instance
registry = GeneratorRegistry()


def register_generator(generator_class: type[Generator]) -> type[Generator]:
    """Decorator to auto-register a generator class."""
    instance = generator_class()
    registry.register(instance)
    return generator_class


# Flag to prevent double discovery
_discovered = False


def discover_generators() -> None:
    """Discover and register all generators in the generators package."""
    global _discovered
    if _discovered:
        return
    _discovered = True

    # Import all generator modules to trigger @register_generator decorators
    from fluxwall.generators import (  # noqa: F401
        color_cycle,
        flowing_curve,
        game_of_life,
        julia,
        l_system,
        mandelbrot,
    )
