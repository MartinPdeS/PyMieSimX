"""Pure orchestration helpers used by the Dash callbacks.

Keeping state conversion and callback error handling here makes the expensive
parts of the dashboard testable without invoking Dash's callback machinery.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PyMieSimX.gui.services import ExperimentValidationError, build_single_figure, run_experiment


@dataclass(frozen=True)
class CallbackExecution:
    """Serializable outcome of a computation requested by a Dash callback."""

    result: dict[str, Any] | None
    run_count: int
    message: str
    level: str


def pair_ids_with_values(ids: list[dict[str, str]], values: list[str]) -> dict[str, str]:
    """Convert dynamic Dash field IDs and values into a flat mapping."""
    return {field_id["name"]: value for field_id, value in zip(ids, values)}


def merge_local_plot_values(settings: dict | None, values: tuple[Any, ...]) -> dict:
    """Overlay values from a plot-local options card onto stored preferences."""
    merged = dict(settings or {})
    names = ("x_scale", "log_y", "font_size", "line_width", "show_legend", "show_grid")
    for name, value in zip(names, values):
        if value is not None:
            merged[name] = value
    return merged


def execute_experiment_callback(
    *,
    source_type: str,
    source_values: list[str],
    source_ids: list[dict[str, str]],
    scatterer_type: str,
    scatterer_values: list[str],
    scatterer_ids: list[dict[str, str]],
    detector_type: str,
    detector_values: list[str],
    detector_ids: list[dict[str, str]],
    measure: str,
    run_count: int | None,
) -> CallbackExecution:
    """Execute a parameter sweep and convert errors into UI-ready state."""
    next_count = int(run_count or 0)
    try:
        result = run_experiment(
            source_type=source_type,
            source_values=pair_ids_with_values(source_ids, source_values),
            scatterer_type=scatterer_type,
            scatterer_values=pair_ids_with_values(scatterer_ids, scatterer_values),
            detector_type=detector_type,
            detector_values=pair_ids_with_values(detector_ids, detector_values),
            measure=measure,
        )
    except ExperimentValidationError as error:
        return CallbackExecution(None, next_count, " ".join(issue.message for issue in error.issues), "error")
    except (TypeError, ValueError, KeyError) as error:
        return CallbackExecution(None, next_count, str(error), "error")

    return CallbackExecution(result, next_count + 1, f"Completed {result['row_count']:,} result rows.", "success")


def execute_single_callback(
    *,
    source_type: str,
    source_values: list[str],
    source_ids: list[dict[str, str]],
    scatterer_type: str,
    scatterer_values: list[str],
    scatterer_ids: list[dict[str, str]],
    representation: str,
    projection: str,
    sampling: int,
    nearfield_mode: list[str] | str | None,
    include_incident_field: list[str] | None,
    run_count: int | None,
) -> CallbackExecution:
    """Execute a particle representation and convert errors into UI state."""
    next_count = int(run_count or 0)
    nearfield_values = nearfield_mode if isinstance(nearfield_mode, list) else ([nearfield_mode] if nearfield_mode else [])
    try:
        figure, summary = build_single_figure(
            source_type=source_type,
            source_values=pair_ids_with_values(source_ids, source_values),
            scatterer_type=scatterer_type,
            scatterer_values=pair_ids_with_values(scatterer_ids, scatterer_values),
            representation=representation,
            projection=projection,
            sampling=sampling or 120,
            nearfield_mode="absolute" if "absolute" in nearfield_values else "real",
            include_incident_field="include" in (include_incident_field or []),
        )
    except (TypeError, ValueError, KeyError) as error:
        return CallbackExecution(None, next_count, str(error), "error")

    return CallbackExecution(
        {"figure": figure.to_plotly_json(), "summary": summary},
        next_count + 1,
        "Representation calculated.",
        "success",
    )
