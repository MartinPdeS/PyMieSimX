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

    application = create_dash_app()
    refresh = _callback(application, "_refresh_admin_dashboard")
    activity = _callback(application, "_refresh_admin_activity")
    assert refresh(0, 0) == (no_update,) * 4
    assert activity(0, 0) is no_update
    with application.server.test_client() as client:
        client.post("/admin/login", data={"token": "secret-token"})
        client.get("/admin")
        assert refresh(0, 0)[:3] == ("12", "5", "7")
        assert activity(0, 0) is not no_update
        monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "rotated")
        assert activity(0, 0) is no_update


def test_admin_sign_in_and_redirect(monkeypatch):
    """Exercise direct navigation, form submission and session-backed routing."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "secret-token")
    application = create_dash_app()
    route = _callback(application, "_route_pages")
    with application.server.test_client() as client:
        assert client.get("/admin?token=secret-token").location == "/admin/login"
        assert route("/admin", "?token=secret-token", 0, 0, 0, {}, {})[0].href == "/admin/login"
        assert b"Administrator sign-in" in client.get("/admin/login").data
        assert client.post("/admin/login", data={"token": "wrong"}).status_code == 403
        response = client.post("/admin/login", data={"token": "secret-token"})
        assert response.status_code == 303
        assert response.location == "/admin"
        assert "Max-Age=1800" in response.headers["Set-Cookie"]
        assert client.get("/admin").status_code == 200
        assert "admin-home-page-visits" in _component_ids(route("/admin", "", 0, 0, 0, {}, {})[0])
        monkeypatch.delenv(ADMIN_TOKEN_ENV_VAR)
        assert client.get("/admin/login").status_code == 404
        assert client.get("/admin").location == "/admin/login"
