"""API tests for the export job flow (queue-backed)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from fluxwall.config import settings
from fluxwall.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'exports_dir', tmp_path / 'exports')
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _wait_terminal(client: TestClient, job_id: str, timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f'/api/export/status/{job_id}')
        assert response.status_code == 200
        body = response.json()
        if body['status'] in ('completed', 'failed', 'cancelled'):
            return body
        time.sleep(0.05)
    raise AssertionError('export did not reach a terminal state in time')


def test_export_mp4_flow(client: TestClient) -> None:
    """Starting an export enqueues a job that completes and serves a file."""
    response = client.post(
        '/api/export',
        json={
            'generator': 'game_of_life',
            'params': {'initial_pattern': 'glider', 'grid_width': 80, 'grid_height': 80},
            'options': {
                'format': 'mp4',
                'iphone_model': 'se',
                'fps': 2,
                'duration_sec': 1.0,
                'quality': 90,
            },
        },
    )
    assert response.status_code == 200
    start = response.json()
    job_id = start['job_id']
    assert start['status_url'] == f'/api/export/status/{job_id}'

    status = _wait_terminal(client, job_id)
    assert status['status'] == 'completed'
    assert status['progress'] == 1.0
    assert status['total_frames'] == 2
    assert status['download_url']

    download = client.get(status['download_url'])
    assert download.status_code == 200
    assert len(download.content) > 0


def test_export_invalid_options_returns_422(client: TestClient) -> None:
    # duration_sec > 30 is rejected by ExportOptions validation (pydantic)
    response = client.post(
        '/api/export',
        json={
            'generator': 'game_of_life',
            'params': {'initial_pattern': 'glider'},
            'options': {'format': 'mp4', 'iphone_model': 'se', 'fps': 2, 'duration_sec': 60.0},
        },
    )
    assert response.status_code == 422


def test_export_unknown_generator_returns_422(client: TestClient) -> None:
    # 'not_a_generator' is not a valid GeneratorType enum value -> FastAPI 422
    response = client.post(
        '/api/export',
        json={
            'generator': 'not_a_generator',
            'params': {},
            'options': {'format': 'mp4', 'iphone_model': 'se', 'fps': 2, 'duration_sec': 1.0},
        },
    )
    assert response.status_code == 422


def test_export_status_unknown_job_returns_404(client: TestClient) -> None:
    response = client.get('/api/export/status/00000000-0000-0000-0000-000000000000')
    assert response.status_code == 404
