"""WSGI entry point for deployments using Gunicorn or another WSGI server."""

from PyMieSimX.gui.interface import server

__all__ = ["server"]
