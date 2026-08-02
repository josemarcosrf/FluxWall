"""Application configuration using pydantic-settings."""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        populate_by_name=True,
        extra='ignore',
    )

    # App
    app_name: str = 'FluxWall'
    app_version: str = '0.1.0'
    debug: bool = False
    # Accept LOG_LEVEL, LOGGER_LEVEL or FLUXWALL_LOG_LEVEL as the env var.
    log_level: str = Field(
        default='INFO',
        validation_alias=AliasChoices('LOG_LEVEL', 'LOGGER_LEVEL', 'FLUXWALL_LOG_LEVEL'),
    )

    # Server
    host: str = '0.0.0.0'
    port: int = 8000
    workers: int = 1

    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    presets_dir: Path = Path(__file__).parent.parent.parent / 'presets'
    exports_dir: Path = Path(__file__).parent.parent.parent / 'exports'
    assets_dir: Path = Path(__file__).parent.parent.parent / 'assets'

    # Generator defaults
    default_width: int = 1290
    default_height: int = 2796
    default_fps: int = 30
    default_duration_sec: float = 3.0
    default_colormap: str = 'magma'

    # Preview
    preview_fps: int = 15
    preview_quality: int = 80

    # Export
    max_export_duration_sec: float = 30.0
    max_export_fps: int = 60
    export_timeout_sec: int = 300

    # Job queue
    max_concurrent_jobs: int = 4
    job_ttl_sec: int = 3600


settings = Settings()
