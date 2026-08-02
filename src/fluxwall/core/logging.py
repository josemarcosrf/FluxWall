"""Console logging configuration for FluxWall."""

from __future__ import annotations

import logging
import sys

from fluxwall.config import settings


def configure_logging(level: str | None = None) -> None:
    """Configure the root logger and uvicorn loggers from the settings.

    The level comes from ``settings.log_level`` (``LOGGER_LEVEL`` /
    ``LOG_LEVEL`` / ``FLUXWALL_LOG_LEVEL`` env vars) unless overridden.
    """
    raw = (level or settings.log_level or 'INFO').upper()
    numeric = getattr(logging, raw, None)
    if not isinstance(numeric, int):
        raw = 'INFO'
        numeric = logging.INFO

    logging.basicConfig(
        level=numeric,
        format='%(asctime)s  %(levelname)-7s %(name)s: %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stdout,
        force=True,
    )

    # Keep uvicorn's own access/error logs at the same threshold so a debug
    # run is fully verbose.
    for name in ('uvicorn', 'uvicorn.error', 'uvicorn.access'):
        logging.getLogger(name).setLevel(numeric)


def get_logger(name: str) -> logging.Logger:
    """Return a module logger (configures logging as a convenience)."""
    if not logging.getLogger().handlers:
        configure_logging()
    return logging.getLogger(name)
