"""Parameter-sweep construction and execution services."""

# ruff: noqa: F401 -- this module intentionally defines a stable service API.

from PyMieSimX.gui.computation import (
    DETECTOR_TYPES,
    MAX_RESULT_FRAME_BYTES,
    MAX_RESULT_PAYLOAD_BYTES,
    MAX_SWEEP_COMBINATIONS,
    RESULT_PAYLOAD_WARNING_BYTES,
    SCATTERER_TYPES,
    SOURCE_TYPES,
    ExperimentValidationError,
    ResultSizeLimitError,
    available_measures,
    build_detector_set,
    build_scatterer_set,
    build_source_set,
    infer_variable_fields,
    run_experiment,
)

__all__ = [name for name in globals() if not name.startswith("_")]
