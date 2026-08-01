"""Async job queue for export operations."""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, cast

from fluxwall.core.models import ExportJob, ExportOptions, GeneratorType


class JobStatus(StrEnum):
    PENDING = 'pending'
    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class Job:
    """Internal job representation."""

    generator: GeneratorType
    params: dict[str, Any]
    options: ExportOptions
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    current_frame: int = 0
    total_frames: int = 0
    output_path: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    callback: Callable | None = None
    # Optional async worker that performs the real export. When set, it owns
    # progress/status mutation and `_execute_job` just awaits it.
    task: Callable[[Job], Awaitable[None]] | None = None

    def to_export_job(self) -> ExportJob:
        return ExportJob(
            id=uuid.UUID(self.id),
            generator=self.generator,
            params=self.params,
            options=self.options,
            status=cast(Any, self.status.value),
            progress=self.progress,
            current_frame=self.current_frame,
            total_frames=self.total_frames,
            output_path=self.output_path,
            error=self.error,
            created_at=self.created_at.timestamp(),
            started_at=self.started_at.timestamp() if self.started_at else None,
            completed_at=self.completed_at.timestamp() if self.completed_at else None,
        )


class JobQueue:
    """Async job queue with worker pool."""

    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        self._queue: deque[Job] = deque()
        self._running: dict[str, Job] = {}
        self._completed: dict[str, Job] = {}
        self._workers: list[asyncio.Task] = []
        self._running_count = 0
        self._shutdown = False

    async def start(self) -> None:
        """Start worker tasks."""
        self._shutdown = False
        for _ in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker())
            self._workers.append(worker)

    async def stop(self) -> None:
        """Stop all workers."""
        self._shutdown = True
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    def enqueue(
        self,
        generator: GeneratorType,
        params: dict[str, Any],
        options: ExportOptions,
        callback: Callable | None = None,
        task: Callable[[Job], Awaitable[None]] | None = None,
    ) -> str:
        """Add job to queue."""
        job = Job(
            generator=generator,
            params=params,
            options=options,
            callback=callback,
            task=task,
        )
        job.status = JobStatus.QUEUED
        self._queue.append(job)
        return job.id

    def get_status(self, job_id: str) -> Job | None:
        """Get job status."""
        if job_id in self._running:
            return self._running[job_id]
        if job_id in self._completed:
            return self._completed[job_id]
        for job in self._queue:
            if job.id == job_id:
                return job
        return None

    def cancel(self, job_id: str) -> bool:
        """Cancel a pending or running job."""
        # Check queue
        for _i, job in enumerate(self._queue):
            if job.id == job_id:
                job.status = JobStatus.CANCELLED
                self._queue.remove(job)
                self._completed[job_id] = job
                return True

        # Check running
        if job_id in self._running:
            job = self._running[job_id]
            job.status = JobStatus.CANCELLED
            return True

        return False

    async def _worker(self) -> None:
        """Worker loop."""
        while not self._shutdown:
            # Get next job
            job = None
            while self._queue and not job:
                candidate = self._queue.popleft()
                if candidate.status != JobStatus.CANCELLED:
                    job = candidate

            if not job:
                await asyncio.sleep(0.1)
                continue

            # Run job
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            self._running[job.id] = job
            self._running_count += 1

            try:
                await self._execute_job(job)
                if job.status != JobStatus.CANCELLED:
                    job.status = JobStatus.COMPLETED
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
            finally:
                job.completed_at = datetime.now()
                job.progress = 1.0
                self._running.pop(job.id, None)
                self._completed[job.id] = job
                self._running_count -= 1

                if job.callback:
                    with contextlib.suppress(Exception):
                        await job.callback(job.to_export_job())

    async def _execute_job(self, job: Job) -> None:
        """Execute the actual export job.

        Delegates to ``job.task`` when provided (set by callers that know how
        to run a real export); otherwise falls back to a simulated loop so the
        queue remains useful on its own.
        """
        if job.task is not None:
            await job.task(job)
            return

        # Placeholder simulation - actual implementation uses generators/exporters
        total = job.options.fps * int(job.options.duration_sec)
        job.total_frames = total

        for i in range(total):
            if job.status == JobStatus.CANCELLED:
                break
            job.current_frame = i + 1
            job.progress = (i + 1) / total
            await asyncio.sleep(0.01)  # Simulate work

        job.output_path = f'/tmp/export_{job.id}.{job.options.format.value}'


# Global job queue
job_queue = JobQueue()


async def init_job_queue(max_concurrent: int = 4) -> JobQueue:
    """Initialize and start the global job queue.

    Reuses the module-level singleton so code that imported ``job_queue`` by
    value (e.g. routes) keeps enqueuing onto the started instance.
    """
    global job_queue
    job_queue.max_concurrent = max_concurrent
    await job_queue.start()
    return job_queue


async def shutdown_job_queue() -> None:
    """Shutdown global job queue."""
    await job_queue.stop()
