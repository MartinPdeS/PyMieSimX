"""Server-side usage counters with PostgreSQL and local-file fallbacks."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
import platform
import threading
from typing import Any

try:
    import psycopg
except Exception:  # pragma: no cover - exercised through fallback behavior.
    psycopg = None


LOGGER = logging.getLogger(__name__)

METRICS_BACKEND_ENV_VAR = "PYMIESIMX_USAGE_METRICS_BACKEND"
METRICS_DATABASE_URL_ENV_VAR = "PYMIESIMX_USAGE_METRICS_DATABASE_URL"
METRICS_PATH_ENV_VAR = "PYMIESIMX_USAGE_METRICS_PATH"
DATABASE_URL_ENV_VAR = "DATABASE_URL"
METRICS_TABLE = "metrics_counters"

METRIC_HOME_PAGE_VISIT_COUNT = "pymiesimx_home_page_visit_count"
METRIC_EXPERIMENT_RUN_COUNT = "pymiesimx_experiment_run_count"
METRIC_SINGLE_RUN_COUNT = "pymiesimx_single_run_count"

_WRITE_LOCK = threading.Lock()


@dataclass(frozen=True)
class UsageMetrics:
    """Aggregate PyMieSimX usage counters."""

    home_page_visit_count: int = 0
    experiment_run_count: int = 0
    single_run_count: int = 0

    def to_dict(self) -> dict[str, int]:
        """Return a JSON-safe mapping."""
        return asdict(self)

    def to_home_page_dict(self) -> dict[str, int]:
        """Return the field names expected by the Home page."""
        return {
            "home_page_visits": self.home_page_visit_count,
            "experiment_runs": self.experiment_run_count,
            "single_runs": self.single_run_count,
        }


def load_usage_metrics() -> UsageMetrics:
    """Load counters from PostgreSQL or the configured local fallback."""
    if _use_postgres_backend():
        try:
            return _load_from_postgres()
        except Exception:
            LOGGER.exception("Failed to load PyMieSimX usage metrics from PostgreSQL; using file fallback.")
    return _load_from_file()


def record_home_page_visit() -> UsageMetrics:
    """Atomically increment the server-side home-page visit counter."""
    return _update(home_page_visit_delta=1, experiment_run_delta=0, single_run_delta=0)


def record_experiment_run() -> UsageMetrics:
    """Atomically increment the completed parameter-sweep counter."""
    return _update(home_page_visit_delta=0, experiment_run_delta=1, single_run_delta=0)


def record_single_run() -> UsageMetrics:
    """Atomically increment the completed particle-explorer counter."""
    return _update(home_page_visit_delta=0, experiment_run_delta=0, single_run_delta=1)


def get_metrics_file_path() -> Path:
    """Resolve the local fallback path."""
    configured_path = os.getenv(METRICS_PATH_ENV_VAR, "").strip()
    if configured_path:
        return Path(configured_path).expanduser().resolve()

    home = Path.home()
    if platform.system() == "Darwin":
        return home / "Library" / "Application Support" / "PyMieSimX" / "usage_metrics.json"
    if platform.system() == "Windows" and os.getenv("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "PyMieSimX" / "usage_metrics.json"
    return home / ".local" / "share" / "PyMieSimX" / "usage_metrics.json"


def _update(*, home_page_visit_delta: int, experiment_run_delta: int, single_run_delta: int) -> UsageMetrics:
    if _use_postgres_backend():
        try:
            return _update_postgres(
                home_page_visit_delta=home_page_visit_delta,
                experiment_run_delta=experiment_run_delta,
                single_run_delta=single_run_delta,
            )
        except Exception:
            LOGGER.exception("Failed to update PyMieSimX usage metrics in PostgreSQL; using file fallback.")

    return _update_file(
        home_page_visit_delta=home_page_visit_delta,
        experiment_run_delta=experiment_run_delta,
        single_run_delta=single_run_delta,
    )


def _load_from_file() -> UsageMetrics:
    path = get_metrics_file_path()
    if not path.exists():
        return UsageMetrics()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return UsageMetrics(**{key: max(0, int(payload.get(key, 0))) for key in UsageMetrics.__dataclass_fields__})
    except Exception:
        LOGGER.exception("Failed to read PyMieSimX usage metrics path=%r", str(path))
        return UsageMetrics()


def _update_file(*, home_page_visit_delta: int, experiment_run_delta: int, single_run_delta: int) -> UsageMetrics:
    with _WRITE_LOCK:
        current = _load_from_file()
        next_metrics = UsageMetrics(
            home_page_visit_count=current.home_page_visit_count + max(0, int(home_page_visit_delta)),
            experiment_run_count=current.experiment_run_count + max(0, int(experiment_run_delta)),
            single_run_count=current.single_run_count + max(0, int(single_run_delta)),
        )
        path = get_metrics_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        temporary_path.write_text(json.dumps(next_metrics.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        temporary_path.replace(path)
    LOGGER.debug("Updated file usage metrics path=%s metrics=%s", path, next_metrics.to_dict())
    return next_metrics


def _use_postgres_backend() -> bool:
    backend = os.getenv(METRICS_BACKEND_ENV_VAR, "file").strip().lower()
    if backend != "postgres":
        return False
    if psycopg is None:
        LOGGER.warning("PostgreSQL metrics requested but psycopg is unavailable; using file fallback.")
        return False
    return bool(_get_database_url())


def _get_database_url() -> str:
    return os.getenv(METRICS_DATABASE_URL_ENV_VAR, "").strip() or os.getenv(DATABASE_URL_ENV_VAR, "").strip()


def _connect_postgres():
    database_url = _get_database_url()
    if not database_url:
        raise RuntimeError("PostgreSQL metrics requested but no database URL is configured.")
    return psycopg.connect(database_url)


def _ensure_table(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {METRICS_TABLE} (
                metric_name TEXT PRIMARY KEY,
                metric_value BIGINT NOT NULL DEFAULT 0,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


def _load_from_postgres() -> UsageMetrics:
    names = (METRIC_HOME_PAGE_VISIT_COUNT, METRIC_EXPERIMENT_RUN_COUNT, METRIC_SINGLE_RUN_COUNT)
    with _connect_postgres() as connection:
        _ensure_table(connection)
        with connection.cursor() as cursor:
            cursor.execute("SELECT metric_name, metric_value FROM metrics_counters WHERE metric_name = ANY(%s)", (list(names),))
            values = {name: max(0, int(value)) for name, value in cursor.fetchall()}
    metrics = UsageMetrics(
        home_page_visit_count=values.get(METRIC_HOME_PAGE_VISIT_COUNT, 0),
        experiment_run_count=values.get(METRIC_EXPERIMENT_RUN_COUNT, 0),
        single_run_count=values.get(METRIC_SINGLE_RUN_COUNT, 0),
    )
    LOGGER.debug("Loaded PostgreSQL usage metrics=%s", metrics.to_dict())
    return metrics


def _update_postgres(*, home_page_visit_delta: int, experiment_run_delta: int, single_run_delta: int) -> UsageMetrics:
    deltas = {
        METRIC_HOME_PAGE_VISIT_COUNT: max(0, int(home_page_visit_delta)),
        METRIC_EXPERIMENT_RUN_COUNT: max(0, int(experiment_run_delta)),
        METRIC_SINGLE_RUN_COUNT: max(0, int(single_run_delta)),
    }
    with _connect_postgres() as connection:
        _ensure_table(connection)
        with connection.cursor() as cursor:
            for metric_name, delta in deltas.items():
                if delta <= 0:
                    continue
                cursor.execute(
                    f"""
                    INSERT INTO {METRICS_TABLE} (metric_name, metric_value)
                    VALUES (%s, %s)
                    ON CONFLICT (metric_name) DO UPDATE SET
                        metric_value = {METRICS_TABLE}.metric_value + EXCLUDED.metric_value,
                        updated_at = NOW()
                    """,
                    (metric_name, delta),
                )
        connection.commit()
    return _load_from_postgres()


__all__ = [
    "UsageMetrics",
    "get_metrics_file_path",
    "load_usage_metrics",
    "record_experiment_run",
    "record_home_page_visit",
    "record_single_run",
]
