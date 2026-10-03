"""Stable, GUI-independent Python API for PyMieSimX computations."""

from PyMieSimX.gui.services import (
    MAX_SWEEP_COMBINATIONS,
    MAX_RESULT_FRAME_BYTES,
    MAX_RESULT_PAYLOAD_BYTES,
    ExperimentValidationError,
    ResultSizeEstimate,
    ResultSizeLimitError,
    ValidationIssue,
    available_measures,
    build_figure,
    build_single_figure,
    estimate_sweep_size,
    export_result_to_csv,
    export_single_result_to_csv,
    estimate_result_size,
    run_experiment,
    validate_experiment_inputs,
)

from PyMieSimX.gui.population_service import compute_population_optics, export_population_to_csv

__all__ = [
    "compute_population_optics",
    "export_population_to_csv",
    "MAX_SWEEP_COMBINATIONS",
    "MAX_RESULT_FRAME_BYTES",
    "MAX_RESULT_PAYLOAD_BYTES",
    "ExperimentValidationError",
    "ResultSizeEstimate",
    "ResultSizeLimitError",
    "ValidationIssue",
    "available_measures",
    "build_figure",
    "build_single_figure",
    "estimate_sweep_size",
    "export_result_to_csv",
    "export_single_result_to_csv",
    "estimate_result_size",
    "run_experiment",
    "validate_experiment_inputs",
]
