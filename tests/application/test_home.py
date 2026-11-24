"""Public visit metrics must be explicitly enabled for a hosted backend."""

import pytest

from PyMieSimX.gui import usage_metrics
from PyMieSimX.gui.pages.home import build_home_page


def _visit_values(component):
    if getattr(component, "id", None) == "home-public-visit-count":
        yield component.children
    children = getattr(component, "children", None)
    for child in children if isinstance(children, (list, tuple)) else [children]:
        if child is not None and not isinstance(child, (str, int, float)):
            yield from _visit_values(child)


@pytest.mark.parametrize("flag,backend,database", [
    (None, "postgres", "postgresql://example/metrics"),
    ("false", "postgres", "postgresql://example/metrics"),
    ("true", "file", ""),
    ("true", "postgres", ""),
])
def test_visit_box_hidden_without_explicit_hosted_configuration(monkeypatch, flag, backend, database):
    monkeypatch.delenv("SHOW_METRIC", raising=False)
    if flag is not None:
        monkeypatch.setenv("SHOW_METRIC", flag)
    monkeypatch.setenv("PYMIESIMX_USAGE_METRICS_BACKEND", backend)
    monkeypatch.setenv("DATABASE_URL", database)
    monkeypatch.delenv("PYMIESIMX_USAGE_METRICS_DATABASE_URL", raising=False)
    monkeypatch.setattr(usage_metrics, "psycopg", object())
    assert list(_visit_values(build_home_page(home_visits=1234))) == []


@pytest.mark.parametrize("count,expected", [(0, ["0"]), (12345, ["12,345"]), (float("nan"), []), (None, []), (-1, [])])
def test_hosted_visit_box_formats_available_counts(monkeypatch, count, expected):
    monkeypatch.setenv("SHOW_METRIC", "true")
    monkeypatch.setenv("PYMIESIMX_USAGE_METRICS_BACKEND", "postgres")
    monkeypatch.setenv("PYMIESIMX_USAGE_METRICS_DATABASE_URL", "postgresql://example/metrics")
    monkeypatch.setattr(usage_metrics, "psycopg", object())
    assert list(_visit_values(build_home_page(home_visits=count))) == expected
