"""Tests for the public API and callback orchestration boundary."""

import PyMieSimX

from PyMieSimX.gui import jobs as jobs_module
from PyMieSimX.gui.callback_helpers import execute_experiment_callback, merge_local_plot_values, pair_ids_with_values
from PyMieSimX.gui.jobs import ExperimentJobManager


def test_public_api_exposes_computational_entry_points_without_gui_symbols():
    assert callable(PyMieSimX.run_experiment)
    assert callable(PyMieSimX.build_figure)
    assert PyMieSimX.MAX_SWEEP_COMBINATIONS == 50_000
    assert PyMieSimX.MAX_RESULT_PAYLOAD_BYTES > 0
    assert isinstance(PyMieSimX.__version__, str)


def test_callback_helpers_convert_state_and_preserve_plot_settings():
    assert pair_ids_with_values([{"name": "wavelength"}], ["650"]) == {"wavelength": "650"}
    assert merge_local_plot_values({"font_size": 12}, (None, True)) == {"font_size": 12, "log_y": True}


def test_experiment_callback_helper_returns_structured_failure():
    execution = execute_experiment_callback(
        source_type="GaussianSet",
        source_values=["-1"],
        source_ids=[{"name": "wavelength"}],
        scatterer_type="SphereSet",
        scatterer_values=[],
        scatterer_ids=[],
        detector_type="None",
        detector_values=[],
        detector_ids=[],
        measure="Qsca",
        run_count=4,
    )

    assert execution.level == "error"
    assert execution.result is None
    assert execution.run_count == 4
    assert execution.message


def test_background_job_manager_tracks_completion(monkeypatch):
    monkeypatch.setattr(jobs_module, "run_experiment", lambda **_kwargs: {"row_count": 2, "rows": []})
    manager = ExperimentJobManager(max_workers=1)

    job_id = manager.submit(measure="Qsca")
    snapshot = manager.snapshot(job_id)
    assert snapshot is not None

    future = manager._jobs[job_id].future
    assert future is not None
    future.result(timeout=2)
    completed = manager.snapshot(job_id)
    assert completed is not None
    assert completed["status"] == "succeeded"
    assert completed["result"]["row_count"] == 2
    manager._executor.shutdown(wait=True)
