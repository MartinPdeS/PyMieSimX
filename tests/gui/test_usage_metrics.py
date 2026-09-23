"""Tests for hosted and local usage-metric behavior."""

from math import isnan

from PyMieSimX.gui import usage_metrics
from PyMieSimX.gui.pages.home import _metric_text


def test_local_metrics_are_unavailable_and_not_persisted(tmp_path, monkeypatch):
    metrics_path = tmp_path / "metrics.json"
    monkeypatch.setenv("PYMIESIMX_USAGE_METRICS_BACKEND", "file")
    monkeypatch.setenv("PYMIESIMX_USAGE_METRICS_PATH", str(metrics_path))

    for metrics in (
        usage_metrics.load_usage_metrics(),
        usage_metrics.record_home_page_visit(),
        usage_metrics.record_experiment_run(),
        usage_metrics.record_single_run(),
    ):
        assert all(isnan(value) for value in metrics.to_home_page_dict().values())
    assert not metrics_path.exists()
    assert _metric_text(float("nan")) == "NaN"


def test_postgres_backend_uses_standard_database_url(monkeypatch):
    monkeypatch.setenv("PYMIESIMX_USAGE_METRICS_BACKEND", "postgres")
    monkeypatch.delenv("PYMIESIMX_USAGE_METRICS_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/metrics")
    monkeypatch.setattr(usage_metrics, "psycopg", object())

    assert usage_metrics._use_postgres_backend() is True
