"""Parsing helpers for dashboard form values."""

from __future__ import annotations

from typing import Any

import numpy as np

from PyMieSim.experiment.polarization_set import PolarizationSet
from PyMieSim.material import SellmeierMaterial, SellmeierMedium, TabulatedMaterial


MAX_EXPRESSION_POINTS = 500


def parse_expression(raw_value: Any) -> Any:
    """Parse scalars, lists, or linear/logarithmic range specifications.

    Ranges use ``start:stop:count`` for linear spacing (the default),
    ``lin:start:stop:count`` for explicit linear spacing, or
    ``log:start:stop:count`` for base-ten logarithmic spacing.
    """
    if raw_value is None:
        return None

    if isinstance(raw_value, (np.ndarray, list, tuple)):
        if len(raw_value) > MAX_EXPRESSION_POINTS:
            raise ValueError(f"An expression cannot contain more than {MAX_EXPRESSION_POINTS} points.")
        return raw_value

    if isinstance(raw_value, (int, float, complex)):
        return raw_value

    text = str(raw_value).strip()

    if text == "":
        return None

    parts = [part.strip() for part in text.split(":")]
    if len(parts) in {3, 4}:
        mode = "lin"
        if len(parts) == 4:
            mode, *parts = parts
            mode = mode.lower()
            if mode not in {"lin", "log"}:
                raise ValueError("Range mode must be 'lin' or 'log'.")

        start_text, stop_text, count_text = parts
        count = int(float(count_text))
        if count <= 0:
            raise ValueError("Range count must be positive.")
        if count > MAX_EXPRESSION_POINTS:
            raise ValueError(f"A range cannot contain more than {MAX_EXPRESSION_POINTS} points.")

        start = float(start_text)
        stop = float(stop_text)
        if mode == "log":
            if start <= 0 or stop <= 0:
                raise ValueError("Logarithmic ranges require positive start and stop values.")
            return np.geomspace(start, stop, count)
        return np.linspace(start, stop, count)

    if "," in text:
        tokens = [_parse_scalar_or_text(token.strip()) for token in text.split(",") if token.strip()]

        if all(not isinstance(token, str) for token in tokens):
            dtype = complex if any(isinstance(token, complex) and not isinstance(token, bool) for token in tokens) else float
            values = np.asarray(tokens, dtype=dtype)
            if len(values) > MAX_EXPRESSION_POINTS:
                raise ValueError(f"An expression cannot contain more than {MAX_EXPRESSION_POINTS} points.")
            return values

        if len(tokens) > MAX_EXPRESSION_POINTS:
            raise ValueError(f"An expression cannot contain more than {MAX_EXPRESSION_POINTS} points.")
        return [str(token) for token in tokens]

    return _parse_scalar_or_text(text)


def parse_numeric_expression(raw_value: Any, *, integer: bool = False) -> Any:
    """Parse a numeric scalar or numeric sequence."""
    parsed = parse_expression(raw_value)

    if parsed is None:
        return None

    if isinstance(parsed, str):
        raise ValueError(f"Expected numeric values, received '{parsed}'.")

    if isinstance(parsed, np.ndarray):
        return parsed.astype(int if integer else float)

    if isinstance(parsed, list):
        if any(isinstance(value, str) for value in parsed):
            raise ValueError(f"Expected numeric values, received '{parsed}'.")
        return np.asarray(parsed, dtype=int if integer else float)

    return int(parsed) if integer else float(parsed)


def parse_quantity_expression(raw_value: Any, unit: Any) -> Any:
    """Parse a numeric expression and attach a Pint unit."""
    parsed = parse_numeric_expression(raw_value)

    if parsed is None:
        return None

    return parsed * unit


def parse_polarization(raw_value: Any, unit: Any) -> PolarizationSet:
    """Parse a polarization angle expression into a ``PolarizationSet``."""
    angles = parse_quantity_expression(raw_value, unit)
    return PolarizationSet(angles=angles)


def parse_mode_numbers(raw_value: Any) -> Any:
    """Parse one or more coherent mode labels."""
    parsed = parse_expression(raw_value)

    if isinstance(parsed, list):
        return parsed

    return parsed


def parse_material_values(raw_value: Any, *, medium: bool = False) -> Any:
    """Parse numeric or named material or medium definitions."""
    parsed = parse_expression(raw_value)

    if parsed is None:
        return None

    if isinstance(parsed, np.ndarray):
        return parsed

    if isinstance(parsed, list):
        return [_resolve_material_entry(value, medium=medium) for value in parsed]

    return _resolve_material_entry(parsed, medium=medium)


def serialize_value(value: Any) -> Any:
    """Convert NumPy and object values into JSON-friendly primitives."""
    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, complex):
        return str(value)

    if isinstance(value, (int, float, str, bool)) or value is None:
        return value

    return str(value)


def _parse_scalar_or_text(text: str) -> Any:
    """Parse one scalar token as float, complex, or raw text."""
    if text == "":
        return None

    try:
        if "j" in text.lower():
            return complex(text.replace("i", "j").replace("I", "j"))
        return float(text)
    except ValueError:
        return text


def _resolve_material_entry(value: Any, *, medium: bool) -> Any:
    """Resolve one material token into either a numeric value or material object."""
    if not isinstance(value, str):
        return value

    constructors = (SellmeierMedium,) if medium else (SellmeierMaterial, TabulatedMaterial)
    last_error = None

    for constructor in constructors:
        try:
            return constructor(value)
        except Exception as error:  # pragma: no cover
            last_error = error

    raise ValueError(f"Unknown {'medium' if medium else 'material'} '{value}'.") from last_error
