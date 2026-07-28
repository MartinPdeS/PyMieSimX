"""Bounded in-process background jobs for expensive dashboard calculations."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from threading import Lock
from uuid import uuid4
from typing import Any

from PyMieSimX.gui.services import run_experiment


LOGGER = logging.getLogger(__name__)
MAX_RETAINED_JOBS = 32


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class _Job:
    job_id: str
    status: str = "pending"
    result: dict[str, Any] | None = None
    error: str | None = None
    submitted_at: str = field(default_factory=_now)
    started_at: str | None = None
    finished_at: str | None = None
    future: Future | None = None


class ExperimentJobManager:
    """Submit and inspect bounded experiment jobs without blocking Dash."""

    def __init__(self, *, max_workers: int = 1) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pymiesimx-worker")
        self._jobs: dict[str, _Job] = {}
        self._lock = Lock()

    def submit(self, **kwargs: Any) -> str:
        """Submit one experiment and return its opaque job identifier."""
        job = _Job(job_id=uuid4().hex)
        with self._lock:
            self._prune_locked()
            self._jobs[job.job_id] = job
            job.future = self._executor.submit(self._run, job.job_id, kwargs)
        LOGGER.info("Submitted experiment job_id=%s queued_jobs=%d", job.job_id, len(self._jobs))
        return job.job_id

    def snapshot(self, job_id: str | None) -> dict[str, Any] | None:
        """Return a JSON-safe snapshot of a job."""
        if not job_id:
            return None
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return {
                "job_id": job.job_id,
                "status": job.status,
                "result": job.result,
                "error": job.error,
                "submitted_at": job.submitted_at,
                "started_at": job.started_at,
                "finished_at": job.finished_at,
            }

    def cancel(self, job_id: str | None) -> bool:
        """Cancel a queued job when it has not started yet."""
        if not job_id:
            return False
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.future is None or not job.future.cancel():
                return False
            job.status = "cancelled"
            job.finished_at = _now()
        LOGGER.info("Cancelled experiment job_id=%s", job_id)
        return True

    def _run(self, job_id: str, kwargs: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.started_at = _now()
        LOGGER.info("Started experiment job_id=%s", job_id)
        try:
            result = run_experiment(**kwargs)
        except Exception as error:  # noqa: BLE001 - job boundary must retain failure state
            with self._lock:
                job = self._jobs[job_id]
                job.status = "failed"
                job.error = str(error)
                job.finished_at = _now()
            LOGGER.exception("Experiment job failed job_id=%s", job_id)
            return

        with self._lock:
            job = self._jobs[job_id]
            job.status = "succeeded"
            job.result = result
            job.finished_at = _now()
        LOGGER.info("Finished experiment job_id=%s rows=%d", job_id, result.get("row_count", 0))

    def _prune_locked(self) -> None:
        completed = [job for job in self._jobs.values() if job.status in {"succeeded", "failed", "cancelled"}]
        for job in sorted(completed, key=lambda item: item.finished_at or item.submitted_at)[: max(0, len(self._jobs) - MAX_RETAINED_JOBS + 1)]:
            self._jobs.pop(job.job_id, None)


experiment_jobs = ExperimentJobManager()


__all__ = ["ExperimentJobManager", "experiment_jobs"]
