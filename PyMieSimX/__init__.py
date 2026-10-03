"""Python API and optional Dash graphical interface for PyMieSim."""

from importlib.metadata import PackageNotFoundError, version

from PyMieSimX.api import (
    MAX_SWEEP_COMBINATIONS,
    MAX_RESULT_FRAME_BYTES,
    MAX_RESULT_PAYLOAD_BYTES,
    ExperimentValidationError,
    ResultSizeEstimate,
    ResultSizeLimitError,
    ValidationIssue,
    compute_population_optics,
    export_population_to_csv,
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

try:
    __version__ = version("PyMieSimX")
except PackageNotFoundError:
    __version__ = "0+unknown"

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
    "__version__",
    "OpticalSetupGUI",
    "create_dash_app",
]


def __getattr__(name: str):
    """Load the optional Dash interface only when it is explicitly requested."""
    if name in {"OpticalSetupGUI", "create_dash_app"}:
        from PyMieSimX.gui.interface import OpticalSetupGUI, create_dash_app

        return {"OpticalSetupGUI": OpticalSetupGUI, "create_dash_app": create_dash_app}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
