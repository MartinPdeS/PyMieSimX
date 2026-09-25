"""Dash application construction and backwards-compatible launcher."""

import json
import logging
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
import webbrowser

from dash import Dash
from flask import Flask, redirect

from PyMieSimX.gui.callbacks import register_callbacks
from PyMieSimX.gui.layout import create_layout
from PyMieSimX.gui.material_catalog import ensure_material_catalog
from PyMieSimX.gui.services import available_measures

LOGGER = logging.getLogger(__name__)
GITHUB_RELEASES_URL = "https://github.com/MartinPdeS/PyMieSimX/releases"
GITHUB_LATEST_RELEASE_API_URL = "https://api.github.com/repos/MartinPdeS/PyMieSimX/releases/latest"
PLATFORM_HINTS = {
    "windows": ("windows", "win", ".exe", ".msi"),
    "macos": ("mac", "darwin", "osx", ".dmg", ".pkg"),
    "linux": ("linux", "manylinux", "appimage", ".deb", ".rpm"),
}


def _initialize_material_catalog() -> None:
    """Prepare PyOptik data before any server builds the dashboard layout."""
    try:
        catalog_file = ensure_material_catalog()
        LOGGER.info("PyOptik material catalog ready at %s", catalog_file)
    except Exception as error:
        LOGGER.warning("Unable to initialize the PyOptik material catalog: %s", error)


def create_dash_app() -> Dash:
    """Create and configure the experiment dashboard Dash application."""
    application = Dash(
        __name__,
        title="PyMieSim Parameter Sweep Lab",
        assets_folder=str(Path(__file__).with_name("assets")),
        suppress_callback_exceptions=True,
    )
    application.index_string = application.index_string.replace(
        "{%favicon%}",
        '<link rel="icon" type="image/svg+xml" href="/assets/pymiesim-favicon.svg?v=3">'
        '<link rel="shortcut icon" type="image/svg+xml" href="/assets/pymiesim-favicon.svg?v=3">',
    )
    _register_latest_download_route(application.server)
    initial_measures = available_measures("SphereSet", "PhotodiodeSet")
    application.layout = create_layout(initial_measures)
    register_callbacks(application, initial_measures)
    LOGGER.debug("Dash application initialized with %d callbacks", len(application.callback_map))
    return application


def _register_latest_download_route(server: Flask) -> None:
    """Register a redirect endpoint for latest platform release downloads."""
    if "download_latest_release" in server.view_functions:
        return

    @server.get("/download/latest/<platform>")
    def download_latest_release(platform: str):
        hints = PLATFORM_HINTS.get(platform.lower())
        if not hints:
            return redirect(GITHUB_RELEASES_URL, code=302)
        try:
            request = Request(
                GITHUB_LATEST_RELEASE_API_URL,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "PyMieSimX-GUI"},
            )
            with urlopen(request, timeout=5) as response:
                payload = json.load(response)
        except (URLError, TimeoutError, OSError, ValueError):
            LOGGER.debug("Unable to query latest release API", exc_info=True)
            return redirect(GITHUB_RELEASES_URL, code=302)

        for asset in payload.get("assets", []) if isinstance(payload, dict) else []:
            if any(hint in str(asset.get("name", "")).lower() for hint in hints):
                download_url = asset.get("browser_download_url")
                if isinstance(download_url, str) and download_url:
                    return redirect(download_url, code=302)
        return redirect(GITHUB_RELEASES_URL, code=302)


class OpticalSetupGUI:
    """Backward-compatible wrapper around the Dash application."""

    def __init__(self) -> None:
        self.app = app

    def run(self, host: str = "0.0.0.0", port: str = "8050", open_browser: bool = False, debug: bool = False) -> None:
        if open_browser:
            webbrowser.open(f"http://{host}:{port}/", new=2)
        self.app.run(debug=debug, host=host, port=port)


_initialize_material_catalog()
app = create_dash_app()
server = app.server


if __name__ == "__main__":
    OpticalSetupGUI().run(host="0.0.0.0", port="8050", debug=True)
