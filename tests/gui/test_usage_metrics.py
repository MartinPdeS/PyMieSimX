"""Tests for server-side usage metrics storage and fallback behavior."""

from PyMieSimX.gui import usage_metrics


def test_file_metrics_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("PYMIESIMX_USAGE_METRICS_BACKEND", "file")
    monkeypatch.setenv("PYMIESIMX_USAGE_METRICS_PATH", str(tmp_path / "metrics.json"))

    assert usage_metrics.load_usage_metrics() == usage_metrics.UsageMetrics()
    usage_metrics.record_home_page_visit()
    usage_metrics.record_home_page_visit()
    usage_metrics.record_experiment_run()
    usage_metrics.record_single_run()

    metrics = usage_metrics.load_usage_metrics()
    assert metrics.to_home_page_dict() == {
        "home_page_visits": 2,
        "experiment_runs": 1,
        "single_runs": 1,
    }


def test_postgres_backend_uses_standard_database_url(monkeypatch):
    monkeypatch.setenv("PYMIESIMX_USAGE_METRICS_BACKEND", "postgres")
    monkeypatch.delenv("PYMIESIMX_USAGE_METRICS_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/metrics")
    monkeypatch.setattr(usage_metrics, "psycopg", object())

    assert usage_metrics._use_postgres_backend() is True
