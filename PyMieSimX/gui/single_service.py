"""Single-particle setup and representation services."""

# ruff: noqa: F401 -- this module intentionally defines a stable service API.

from PyMieSimX.gui.computation import (
    NEARFIELD_SCATTERER_TYPES,
    SINGLE_SCATTERER_TYPES,
    SINGLE_SOURCE_TYPES,
    _nearfield_scatterer_shapes,
    build_single_figure,
    build_single_setup,
)

__all__ = [name for name in globals() if not name.startswith("_")]
