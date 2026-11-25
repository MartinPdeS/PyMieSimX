"""Regression tests for inline visit locations and trusted proxy resolution."""

import sys
from contextlib import nullcontext
from unittest.mock import Mock
from flask import Flask
from PyMieSimX.gui import admin
from PyMieSimX.gui.visit_location import request_location


def test_lookup_uses_trusted_proxy_and_formats_partial_location(*, monkeypatch):
    """Use the client reported by the final trusted proxy, including partial records."""
    reader = Mock()
    reader.get.return_value = {"city": {"names": {"en": "London"}}, "country": {"iso_code": "GB"}}
    module = Mock()
    module.open_database.return_value = nullcontext(reader)
    monkeypatch.setitem(sys.modules, "maxminddb", module)
    monkeypatch.setenv("PYMIESIMX_GEOIP_DATABASE", "test.mmdb")
    monkeypatch.setenv("PYMIESIMX_TRUSTED_PROXY_COUNT", "1")
    with Flask(__name__).test_request_context(headers={"X-Forwarded-For": "1.1.1.1, 81.2.69.160"}):
        assert request_location() == "London, GB"
    reader.get.assert_called_once_with("81.2.69.160")


def test_activity_displays_locations_including_legacy_rows(*, monkeypatch):
    """Display the available location and the fallback directly in table cells."""
    visits = [("now", "/", "London, GB"), ("earlier", "/single", None)]
    monkeypatch.setattr(admin.usage_metrics, "load_page_visits", lambda: visits)
    header, body = admin.build_recent_visits().children.children
    assert [cell.children for cell in header.children.children] == ["Visited at", "Page", "Location"]
    assert [row.children[-1].children for row in body.children] == ["London, GB", "Unavailable"]
