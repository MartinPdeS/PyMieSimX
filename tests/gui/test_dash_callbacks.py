"""Integration tests for registered Dash callback behavior."""

from math import isnan
from io import StringIO

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from dash import no_update

from PyMieSimX.gui import callbacks, usage_metrics
from PyMieSimX.gui.callback_helpers import CallbackExecution
from PyMieSimX.gui.interface import create_dash_app


def _callback(application, name):
    for definition in application.callback_map.values():
        callback = getattr(definition["callback"], "__wrapped__", None)
        if callback is not None and callback.__name__ == name:
            return callback
    raise AssertionError(f"callback {name!r} is not registered")


def _experiment_args(wavelength="650", diameter="500", material="1.4"):
    return (
        "GaussianSet", [wavelength, "0", "1e-3", "0.2"],
        [{"name": name} for name in ("wavelength", "polarization", "optical_power", "numerical_aperture")],
        "SphereSet", [diameter, material, "1.0"],
        [{"name": name} for name in ("diameter", "material", "medium")],
        "None", [], [], "Qsca",
    )


def _message(banner):
    return banner.children[1].children


def test_navigation_and_local_metrics(monkeypatch):
    application = create_dash_app()
    monkeypatch.setattr(usage_metrics, "record_home_page_visit", lambda: usage_metrics.UsageMetrics())
    route = _callback(application, "_route_pages")

    home = route("/", "", 0, 0, 0, {"theme": "light"}, {})
    experiment = route("/experiment", "", home[-1], 0, 0, {"theme": "light"}, {})

    assert home[1].endswith("active")
    assert isnan(home[-1])
    assert experiment[2].endswith("active")
    assert callbacks._counter(float("nan")) == 0


def test_home_route_uses_newly_recorded_server_count(monkeypatch):
    application = create_dash_app()
    monkeypatch.setattr(usage_metrics, "record_home_page_visit", lambda: usage_metrics.UsageMetrics(home_page_visit_count=4321))
    displayed = []
    original = callbacks.build_home_page
    monkeypatch.setattr(callbacks, "build_home_page", lambda **kwargs: displayed.append(kwargs["home_visits"]) or original(**kwargs))
    home = _callback(application, "_route_pages")("/", "", 999999, 0, 0, {"theme": "light"}, {})
    assert home[-1] == 4321
    assert displayed == [4321]


def test_validation_submission_cancellation_and_polling(monkeypatch):
    application = create_dash_app()
    validate = _callback(application, "_validate_fields")
    classes, errors = validate(
        ["-1"],
        [{"section": "source", "name": "wavelength"}],
        "GaussianSet", "SphereSet", "None", "Gaussian", "Sphere",
    )
    assert classes == ["field-input field-input-invalid"]
    assert errors[0]

    cancelled = []
    monkeypatch.setattr(callbacks.experiment_jobs, "cancel", lambda job_id: cancelled.append(job_id) or True)
    monkeypatch.setattr(callbacks.experiment_jobs, "submit", lambda **_kwargs: "new-job")
    submit = _callback(application, "_submit_experiment")
    job, polling_disabled, run_disabled, status = submit(
        1,
        "GaussianSet", ["650", "0", "1e-3", "0.2"],
        [{"name": name} for name in ("wavelength", "polarization", "optical_power", "numerical_aperture")],
        "SphereSet", ["500", "1.4", "1.0"],
        [{"name": name} for name in ("diameter", "material", "medium")],
        "None", [], [], "Qsca", {"job_id": "old-job"},
    )
    assert job == {"job_id": "new-job"}
    assert cancelled == ["old-job"]
    assert polling_disabled is False
    assert run_disabled is True
    assert _message(status).startswith("Queued.")

    result = {"rows": [{"Qsca": 1.0}], "columns": ["Qsca"], "parameter_columns": [], "measure": "Qsca", "units": {}, "row_count": 1}
    monkeypatch.setattr(callbacks.experiment_jobs, "snapshot", lambda _job_id: {
        "job_id": "new-job", "status": "succeeded", "result": result, "error": None,
        "submitted_at": "now", "started_at": "now", "finished_at": "now",
    })
    poll = _callback(application, "_poll_experiment_job")
    completed, count, disabled, run_disabled, status = poll(1, job, 2)
    assert completed == result
    assert count == 3
    assert disabled is True
    assert run_disabled is False
    assert _message(status) == "Completed. 1 result rows."
    assert status.role == "status"


def test_plot_and_csv_callbacks():
    application = create_dash_app()
    result = {"rows": [{"diameter": 100.0, "Qsca": 1.0}], "columns": ["diameter", "Qsca"], "parameter_columns": ["diameter"], "measure": "Qsca", "units": {}, "row_count": 1}

    update_plot = _callback(application, "_update_outputs")
    figure = update_plot(result, "diameter", {}, {"theme": "light"}, None, None, None, None, None, None, "cartesian")
    assert len(figure.data) == 1

    export = _callback(application, "_export_csv")
    assert export(0, result, "Qsca") is no_update
    download = export(1, result, "Qsca")
    assert download["filename"] == "pymiesim_Qsca.csv"
    assert "Qsca" in download["content"]


@pytest.mark.parametrize("encoded", [False, True], ids=["plain", "typed-arrays"])
@pytest.mark.parametrize("kind", ["scatter", "implicit-x", "scatterpolar", "heatmap", "surface"])
def test_particle_explorer_csv_preserves_coordinates_and_values(kind, encoded):
    def array(values):
        return np.array(values, dtype=float) if encoded else values

    if kind in {"scatter", "implicit-x", "scatterpolar"}:
        x, y = [10, 20, 40], [1, 3, 7]
        if kind == "scatterpolar":
            trace = go.Scatterpolar(theta=array(x), r=array(y), name="field")
            expected = {"series": ["field"] * 3, "theta": x, "r": y}
        else:
            trace = go.Scatter(y=array(y), name="field")
            if kind == "scatter":
                trace.x = array(x)
            expected = {"series": ["field"] * 3, "x": x if kind == "scatter" else [0, 1, 2], "value": y}
    elif kind == "heatmap":
        trace = go.Heatmap(x=array([10, 20, 40]), y=array([-5, 15]), z=array([[1, 2, 3], [7, 8, 9]]), name="field")
        expected = {"series": ["field"] * 6, "x": [10, 20, 40] * 2, "y": [-5] * 3 + [15] * 3, "value": [1, 2, 3, 7, 8, 9]}
    else:
        trace = go.Surface(
            x=array([[10, 20, 40], [50, 60, 80]]), y=array([[-5, -4, -3], [15, 16, 17]]),
            z=array([[1, 2, 3], [7, 8, 9]]), surfacecolor=array([[11, 12, 13], [21, 22, 23]]), name="field",
        )
        expected = {
            "series": ["field"] * 6, "x": [10, 20, 40, 50, 60, 80], "y": [-5, -4, -3, 15, 16, 17],
            "z": [1, 2, 3, 7, 8, 9], "value": [11, 12, 13, 21, 22, 23],
        }

    result = {"figure": go.Figure(trace).to_plotly_json()}
    export = _callback(create_dash_app(), "_export_single_csv")
    assert export(0, result) is no_update
    assert export(1, None) is no_update
    download = export(1, result)
    assert download["filename"] == "pymiesim_particle_explorer.csv"
    pd.testing.assert_frame_equal(pd.read_csv(StringIO(download["content"])), pd.DataFrame(expected), check_dtype=False)


@pytest.mark.parametrize("selected, expected", [
    ("Qsca", ["Qsca"]),
    (["Qsca", "coupling", "Qext"], ["Qsca", "Qext"]),
    (["coupling"], ["Qsca"]),
    ([], []),
])
def test_measure_options_preserve_supported_selections(selected, expected):
    update = _callback(create_dash_app(), "_update_measure_options")
    options, value, alert = update("SphereSet", "None", selected)
    assert value == expected
    assert "coupling" not in {option["value"] for option in options}
    assert alert == {}
    _, value, alert = update("SphereSet", "PhotodiodeSet", ["Qsca", "coupling"])
    assert value == ["Qsca", "coupling"]
    assert alert == {"display": "none"}


def test_multiple_measure_submission(monkeypatch):
    application = create_dash_app()
    captured = {}

    def submit_job(**kwargs):
        captured.update(kwargs)
        return "multi-job"

    monkeypatch.setattr(callbacks.experiment_jobs, "submit", submit_job)
    args = (*_experiment_args(diameter="100,200")[:-1], ["Qsca", "Qabs", "Qext"])
    response = _callback(application, "_submit_experiment")(1, *args, None)
    assert response[:3] == ({"job_id": "multi-job"}, False, True)
    assert captured["measure"] == ["Qsca", "Qabs", "Qext"]


def test_export_filename_uses_computed_measures_after_selection_changes():
    application = create_dash_app()
    result = {
        "measure": "Qsca", "measures": ["Qsca", "Qext"],
        "rows": [{"diameter": 100, "Qsca": 1, "Qext": 2}],
        "columns": ["diameter", "Qsca", "Qext"], "parameter_columns": ["diameter"],
        "units": {}, "row_count": 1,
    }
    download = _callback(application, "_export_csv")(1, result, ["Qabs"])
    assert download["filename"] == "pymiesim_Qsca_Qext.csv"
    assert "diameter,Qsca,Qext" in download["content"]


@pytest.mark.parametrize("clicks", [None, 0])
def test_experiment_page_initialization_does_not_submit(monkeypatch, clicks):
    application = create_dash_app()

    def unexpected_submit(**_kwargs):
        pytest.fail("Page initialization must not submit an experiment")

    monkeypatch.setattr(callbacks.experiment_jobs, "submit", unexpected_submit)
    submit = _callback(application, "_submit_experiment")
    assert submit(
        clicks,
        "GaussianSet", ["650", "0", "1e-3", "0.2"],
        [{"name": name} for name in ("wavelength", "polarization", "optical_power", "numerical_aperture")],
        "SphereSet", ["500", "1.4", "1.0"],
        [{"name": name} for name in ("diameter", "material", "medium")],
        "None", [], [], "Qsca", None,
    ) == (no_update, no_update, no_update, no_update)


@pytest.mark.parametrize("job_data", [None, {"job_id": "missing-job"}])
def test_missing_experiment_job_reenables_run(monkeypatch, job_data):
    application = create_dash_app()
    monkeypatch.setattr(callbacks.experiment_jobs, "snapshot", lambda _job_id: None)
    poll = _callback(application, "_poll_experiment_job")

    response = poll(1, job_data, 2)
    assert response[:4] == (no_update, no_update, True, False)
    if job_data:
        assert "Run interrupted" in _message(response[4])
        assert response[4].role == "alert"
    else:
        assert response[4] is no_update


@pytest.mark.parametrize("status", ["pending", "running", "failed", "cancelled"])
def test_experiment_polling_button_state(monkeypatch, status):
    application = create_dash_app()
    monkeypatch.setattr(callbacks.experiment_jobs, "snapshot", lambda _job_id: {
        "job_id": "job", "status": status, "error": "failed" if status == "failed" else None,
    })
    poll = _callback(application, "_poll_experiment_job")

    active = status in {"pending", "running"}
    response = poll(1, {"job_id": "job"}, 2)
    assert response[:4] == (no_update, no_update, not active, active)
    expected = {"pending": "Queued.", "running": "Running.", "failed": "Run failed: failed", "cancelled": "Run cancelled."}
    assert _message(response[4]).startswith(expected[status])
    assert response[4].role == ("alert" if status == "failed" else "status")


def test_rejected_experiment_shows_validation_error(monkeypatch):
    application = create_dash_app()

    def unexpected_submit(**_kwargs):
        pytest.fail("Invalid input must not start a job")

    monkeypatch.setattr(callbacks.experiment_jobs, "submit", unexpected_submit)
    submit = _callback(application, "_submit_experiment")
    response = submit(1, *_experiment_args(wavelength="-1"), None)
    assert response[:3] == (None, True, False)
    assert "Cannot run: wavelength:" in _message(response[3])
    assert response[3].role == "alert"


def test_submission_failure_is_visible_and_recoverable(monkeypatch):
    application = create_dash_app()

    def fail_submit(**_kwargs):
        raise RuntimeError("Worker unavailable")

    monkeypatch.setattr(callbacks.experiment_jobs, "submit", fail_submit)
    submit = _callback(application, "_submit_experiment")
    response = submit(1, *_experiment_args(), None)
    assert response[:3] == (None, True, False)
    assert "Worker unavailable" in _message(response[3])
    assert "retry" in _message(response[3])
    assert response[3].role == "alert"


def test_single_computation_waits_for_run(monkeypatch):
    application = create_dash_app()
    captured = {}

    def execute(**kwargs):
        captured.update(kwargs)
        return CallbackExecution({"figure": {}, "summary": {}}, 2, "done", "success")

    monkeypatch.setattr(callbacks, "execute_single_callback", execute)
    monkeypatch.setattr(usage_metrics, "record_single_run", lambda: None)
    run_single = _callback(application, "_run_single")
    definition = next(
        definition for definition in application.callback_map.values()
        if getattr(definition["callback"], "__wrapped__", None) is run_single
    )
    assert definition["inputs"] == [{"id": "run-single-button", "property": "n_clicks"}]
    assert {"id": "single-projection", "property": "value"} in definition["state"]
    assert {"id": "single-representation", "property": "value"} in definition["state"]
    registration = next(
        entry for entry in application._callback_list
        if entry["output"] == "..single-result.data...single-run-count.data.."
    )
    assert registration["running"]["running"]["single-graph-loading.display"] == "show"
    assert registration["running"]["runningOff"]["single-graph-loading.display"] == "auto"

    for clicks in (None, 0):
        assert run_single(
            clicks, "3d_radial", "Gaussian", [], [], "Sphere", [], [],
            "spf", 120, [], [], 1,
        ) == (no_update, no_update)
    assert captured == {}

    result, run_count = run_single(
        1,
        "3d_radial",
        "Gaussian",
        [],
        [],
        "Sphere",
        [],
        [],
        "spf",
        120,
        [],
        [],
        1,
    )

    assert captured["projection"] == "3d_radial"
    assert captured["representation"] == "spf"
    assert result == {"figure": {}, "summary": {}}
    assert run_count == 2


def test_sweep_computing_message_covers_background_job():
    application = create_dash_app()
    show_computing = _callback(application, "_show_experiment_computing")
    assert show_computing(True) == "show"
    assert show_computing(False) == "auto"
