"""Tests for the public API and callback orchestration boundary."""

from threading import Event
import pytest
import PyMieSimX
from PyMieSimX._version import __version__ as documented_version

from PyMieSimX.gui import jobs as jobs_module
from PyMieSimX.gui.callback_helpers import execute_experiment_callback, merge_local_plot_values, pair_ids_with_values
from PyMieSimX.gui.jobs import ExperimentJobManager


def test_public_api_exposes_computational_entry_points_without_gui_symbols():
    assert callable(PyMieSimX.run_experiment)
    assert callable(PyMieSimX.build_figure)
    assert PyMieSimX.MAX_SWEEP_COMBINATIONS == 50_000
    assert PyMieSimX.MAX_RESULT_PAYLOAD_BYTES > 0
    assert isinstance(PyMieSimX.__version__, str)
    assert PyMieSimX.__version__ == documented_version


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
    monkeypatch.setattr(jobs_module, "execute_experiment", lambda **_kwargs: {"row_count": 2, "rows": []})
    manager = ExperimentJobManager(max_workers=1)

    job_id = manager.submit(request=None)
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

def test_scan_queue_rejects_new_work_at_capacity(monkeypatch):
    """Free a queued slot by cancelling a pending scan."""
    release_worker = Event()
    monkeypatch.setattr(jobs_module, "MAX_ACTIVE_JOBS", 2)
    monkeypatch.setattr(jobs_module, "execute_experiment", lambda **_: release_worker.wait(5) and {"row_count": 0})
    manager = ExperimentJobManager(max_workers=1)
    try:
        manager.submit(request=None)
        queued = manager.submit(request=None)
        with pytest.raises(jobs_module.ExperimentQueueFull):
            manager.submit(request=None)
        assert manager.cancel(queued)
        assert manager.submit(request=None)
    finally:
        release_worker.set()
        manager._executor.shutdown(wait=True)
