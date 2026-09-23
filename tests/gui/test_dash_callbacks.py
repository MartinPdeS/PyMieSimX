"""Integration tests for registered Dash callback behavior."""

from math import isnan

from dash import no_update

from PyMieSimX.gui import callbacks, usage_metrics
from PyMieSimX.gui.interface import create_dash_app


def _callback(application, name):
    for definition in application.callback_map.values():
        callback = getattr(definition["callback"], "__wrapped__", None)
        if callback is not None and callback.__name__ == name:
            return callback
    raise AssertionError(f"callback {name!r} is not registered")


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


def test_validation_submission_cancellation_and_polling(monkeypatch):
    application = create_dash_app()
    validate = _callback(application, "_validate_fields")
    classes = validate(
        ["-1"],
        [{"section": "source", "name": "wavelength"}],
        "GaussianSet", "SphereSet", "None", "Gaussian", "Sphere",
    )
    assert classes == ["field-input field-input-invalid"]

    cancelled = []
    monkeypatch.setattr(callbacks.experiment_jobs, "cancel", lambda job_id: cancelled.append(job_id) or True)
    monkeypatch.setattr(callbacks.experiment_jobs, "submit", lambda **_kwargs: "new-job")
    submit = _callback(application, "_submit_experiment")
    job, status, polling_disabled = submit(
        "GaussianSet", ["650", "0", "1e-3", "0.2"],
        [{"name": name} for name in ("wavelength", "polarization", "optical_power", "numerical_aperture")],
        "SphereSet", ["500", "1.4", "1.0"],
        [{"name": name} for name in ("diameter", "material", "medium")],
        "None", [], [], "Qsca", {"job_id": "old-job"},
    )
    assert job == {"job_id": "new-job"}
    assert cancelled == ["old-job"]
    assert "Queued" in status.children
    assert polling_disabled is False

    result = {"rows": [{"Qsca": 1.0}], "columns": ["Qsca"], "parameter_columns": [], "measure": "Qsca", "units": {}, "row_count": 1}
    monkeypatch.setattr(callbacks.experiment_jobs, "snapshot", lambda _job_id: {
        "job_id": "new-job", "status": "succeeded", "result": result, "error": None,
        "submitted_at": "now", "started_at": "now", "finished_at": "now",
    })
    poll = _callback(application, "_poll_experiment_job")
    completed, count, message, disabled = poll(1, job, 2)
    assert completed == result
    assert count == 3
    assert message is None
    assert disabled is True


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
