"""Regression tests for inline visit locations and trusted proxy resolution."""

from io import BytesIO
from unittest.mock import Mock
from flask import Flask
from PyMieSimX.gui import admin, visit_location
from PyMieSimX.gui.visit_location import request_location


def test_lookup_uses_trusted_proxy_and_formats_partial_location(*, monkeypatch):
    """Use the client reported by the final trusted proxy, including partial records."""
    visit_location._lookup_location.cache_clear()
    lookup = Mock(return_value=BytesIO(b'{"city": "London", "country": "GB"}'))
    monkeypatch.setattr(visit_location, "urlopen", lookup)
    monkeypatch.setenv("PYMIESIMX_IPINFO_TOKEN", "test-token")
    monkeypatch.setenv("PYMIESIMX_TRUSTED_PROXY_COUNT", "1")
    with Flask(__name__).test_request_context(headers={"X-Forwarded-For": "1.1.1.1, 81.2.69.160"}):
        assert request_location() == "London, GB"
        assert request_location() == "London, GB"
    lookup.assert_called_once()
    sent_request = lookup.call_args.args[0]
    assert sent_request.full_url == "https://ipinfo.io/81.2.69.160/json"
    assert sent_request.get_header("Authorization") == "Bearer test-token"


def test_private_visits_and_failed_lookups(*, monkeypatch):
    """Skip private addresses and recover from a failed unauthenticated lookup."""
    visit_location._lookup_location.cache_clear()
    lookup = Mock(side_effect=[TimeoutError(), BytesIO(b'{"region":"England"}')])
    monkeypatch.setattr(visit_location, "urlopen", lookup)
    monkeypatch.delenv("PYMIESIMX_IPINFO_TOKEN", raising=False)
    monkeypatch.setenv("PYMIESIMX_TRUSTED_PROXY_COUNT", "0")
    app = Flask(__name__)
    with app.test_request_context(environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        assert request_location() == "Unavailable"
    lookup.assert_not_called()
    with app.test_request_context(environ_base={"REMOTE_ADDR": "8.8.8.8"}):
        assert request_location() == "Unavailable"
        assert request_location() == "England"
    assert lookup.call_args.args[0].get_header("Authorization") is None


def test_activity_displays_locations_including_legacy_rows(*, monkeypatch):
    """Display the available location and the fallback directly in table cells."""
    visits = [("now", "/", "London, GB"), ("earlier", "/single", None)]
    monkeypatch.setattr(admin.usage_metrics, "load_page_visits", lambda: visits)
    header, body = admin.build_recent_visits().children.children
    assert [cell.children for cell in header.children.children] == ["Visited at", "Page", "Location"]
    assert [row.children[-1].children for row in body.children] == ["London, GB", "Unavailable"]
