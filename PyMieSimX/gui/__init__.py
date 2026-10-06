"""Dash dashboard components for PyMieSimX."""

__all__ = ["OpticalSetupGUI", "create_dash_app"]


def __getattr__(name: str):
    """Load the Dash application lazily for computational-only imports."""
    if name in __all__:
        from PyMieSimX.gui.interface import OpticalSetupGUI, create_dash_app

        return {"OpticalSetupGUI": OpticalSetupGUI, "create_dash_app": create_dash_app}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
