#!/usr/bin/env python
"""Regression tests for the dashboard command-line interface."""

from pathlib import Path

from PyMieSimX.__main__ import _build_argument_parser
from PyMieSimX.gui.interface import _initialize_material_catalog, create_dash_app
from PyMieSimX.gui import interface, material_catalog


def test_cli_defaults_are_stable():
    args = _build_argument_parser().parse_args([])

    assert args.host == "0.0.0.0"
    assert args.port == "8050"
    assert args.debug is False
    assert args.no_browser is False


def test_cli_accepts_server_options():
    args = _build_argument_parser().parse_args(
        ["--host", "127.0.0.1", "--port", "9000", "--debug", "--no-browser"]
    )

    assert args.host == "127.0.0.1"
    assert args.port == "9000"
    assert args.debug is True
    assert args.no_browser is True


def test_dashboard_registers_sidebar_routes():
    app = create_dash_app()

    assert any("page-content.children" in callback_id for callback_id in app.callback_map)


def test_material_catalog_setup_reuses_or_downloads_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("PYMIESIM_PYOPTIK_DATA_ROOT", str(tmp_path))
    downloaded = []
    monkeypatch.setattr(material_catalog, "download_snapshot", lambda data_root: downloaded.append(data_root))

    assert material_catalog.ensure_material_catalog() == tmp_path / "catalog-nk.yml"
    assert downloaded == [tmp_path]

    (tmp_path / "catalog-nk.yml").touch()
    downloaded.clear()
    assert material_catalog.ensure_material_catalog() == Path(tmp_path) / "catalog-nk.yml"
    assert downloaded == []


def test_server_startup_initializes_material_catalog(monkeypatch):
    initialized = []
    monkeypatch.setattr(interface, "ensure_material_catalog", lambda: initialized.append(True) or Path("catalog-nk.yml"))

    _initialize_material_catalog()

    assert initialized == [True]
