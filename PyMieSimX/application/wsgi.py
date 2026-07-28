"""WSGI entry point for deployments using Gunicorn or another WSGI server."""

from PyMieSimX.__main__ import configure_logging

configure_logging(debug=False)

from PyMieSimX.gui.interface import server  # noqa: E402

__all__ = ["server"]
