"""Compatibility facade for the focused computational service modules.

New code should import from ``experiment_service``, ``validation``,
``plotting``, or ``single_service``. Existing imports remain supported.
"""

# ruff: noqa: F401,F403 -- compatibility facade intentionally re-exports names.

from PyMieSimX.gui.computation import *
from PyMieSimX.gui.computation import (
    _infer_variable_fields_for_section,
    _is_angular_unit,
    _parse_field_value,
    _parse_section_fields,
    _validate_positive_field,
    _value_cardinality,
)
