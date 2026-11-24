"""Tests for the hidden, token-gated administration page."""

from dash import no_update

from PyMieSimX.gui import usage_metrics
from PyMieSimX.gui.admin import (
    ADMIN_TOKEN_ENV_VAR,
    build_admin_page,
    collect_admin_dashboard_data,
    dashboard_values,
    is_admin_access_granted,
)
from PyMieSimX.gui.interface import create_dash_app


def _component_ids(component) -> set[str]:
    component_id = getattr(component, "id", None)
    result = {component_id} if isinstance(component_id, str) else set()
    children = getattr(component, "children", None)
    for child in children if isinstance(children, (list, tuple)) else ([children] if children is not None else []):
        result.update(_component_ids(child))
    return result


def _callback(application, name):
    for definition in application.callback_map.values():
        callback = getattr(definition["callback"], "__wrapped__", None)
        if callback is not None and callback.__name__ == name:
            return callback
    raise AssertionError(f"callback {name!r} is not registered")


def test_admin_token_must_be_configured_and_match(monkeypatch):
    monkeypatch.delenv(ADMIN_TOKEN_ENV_VAR, raising=False)
    assert not is_admin_access_granted("anything")

    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "secret-token")
    assert is_admin_access_granted("secret-token")
    assert not is_admin_access_granted("secret-token-extra")
    assert not is_admin_access_granted(None)


def test_admin_layout_is_hidden_without_valid_token(monkeypatch):
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "secret-token")

    denied_ids = _component_ids(build_admin_page("wrong-token"))
    allowed_ids = _component_ids(build_admin_page("secret-token"))

    assert "admin-home-page-visits" not in denied_ids
    assert "admin-home-page-visits" in allowed_ids
    assert "admin-experiment-runs" in allowed_ids
    assert "admin-single-runs" in allowed_ids
    assert "admin-refresh-button" in allowed_ids


def test_admin_dashboard_loads_metrics_and_rechecks_token(monkeypatch):
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "secret-token")
    metrics = usage_metrics.UsageMetrics(12, 5, 7)
    monkeypatch.setattr(usage_metrics, "load_usage_metrics", lambda: metrics)

    data = collect_admin_dashboard_data()
    assert dashboard_values(data)[:3] == ("12", "5", "7")

    refresh = _callback(create_dash_app(), "_refresh_admin_dashboard")
    assert refresh(0, 0, "?token=secret-token")[:3] == ("12", "5", "7")
    assert refresh(0, 0, "?token=wrong") == (no_update, no_update, no_update, no_update)


def test_admin_route_reads_token_from_query_string(monkeypatch):
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "secret-token")
    route = _callback(create_dash_app(), "_route_pages")

    denied = route("/admin", "?token=wrong", 0, 0, 0, {"theme": "light"}, {})
    allowed = route("/admin", "?token=secret-token", 0, 0, 0, {"theme": "light"}, {})

    assert "admin-home-page-visits" not in _component_ids(denied[0])
    assert "admin-home-page-visits" in _component_ids(allowed[0])
