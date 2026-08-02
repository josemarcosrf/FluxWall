"""Tests for the async job queue."""

from __future__ import annotations

import asyncio

from fluxwall.core.job_queue import Job, JobQueue, JobStatus
from fluxwall.core.models import ExportOptions, GeneratorType


async def _wait_terminal(queue: JobQueue, job_id: str, timeout: float = 5.0) -> Job:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        job = queue.get_status(job_id)
        if job and job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return job
        await asyncio.sleep(0.01)
    raise AssertionError('job did not reach terminal state in time')


async def test_custom_task_runs_and_reports_progress() -> None:
    queue = JobQueue(max_concurrent=1)
    await queue.start()
    try:

        async def task(job: Job) -> None:
            job.total_frames = 10
            for i in range(10):
                job.current_frame = i + 1
                job.progress = (i + 1) / 10
                await asyncio.sleep(0)
            job.output_path = '/tmp/export_test.mp4'

        job_id = queue.enqueue(
            generator=GeneratorType.MANDELBROT,
            params={},
            options=ExportOptions(fps=10, duration_sec=1.0),
            task=task,
        )

        job = await _wait_terminal(queue, job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.progress == 1.0
        assert job.total_frames == 10
        assert job.output_path == '/tmp/export_test.mp4'
    finally:
        await queue.stop()


async def test_placeholder_job_reports_progress() -> None:
    queue = JobQueue(max_concurrent=1)
    await queue.start()
    try:
        job_id = queue.enqueue(
            generator=GeneratorType.MANDELBROT,
            params={},
            options=ExportOptions(fps=20, duration_sec=1.0),
        )

        job = await _wait_terminal(queue, job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.total_frames == 20
        assert job.progress == 1.0
    finally:
        await queue.stop()


async def test_cancel_queued_job() -> None:
    queue = JobQueue(max_concurrent=0)
    await queue.start()
    try:
        job_id = queue.enqueue(generator=GeneratorType.MANDELBROT, params={}, options=ExportOptions())
        assert queue.cancel(job_id) is True
        job = queue.get_status(job_id)
        assert job is not None
        assert job.status == JobStatus.CANCELLED
    finally:
        await queue.stop()


async def test_status_unknown_returns_none() -> None:
    queue = JobQueue(max_concurrent=0)
    assert queue.get_status('does-not-exist') is None
