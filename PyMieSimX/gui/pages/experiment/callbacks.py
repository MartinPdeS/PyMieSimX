"""Dash callbacks for the Parameter Scan job lifecycle."""

import logging
from dash import ALL, Dash, Input, Output, State, no_update
from PyMieSimX.gui import usage_metrics
from PyMieSimX.gui.callback_helpers import pair_ids_with_values as _pair_ids_with_values, status_banner
from PyMieSimX.gui.computation import ExperimentValidationError, prepare_experiment
from PyMieSimX.gui.jobs import ExperimentQueueFull, experiment_jobs

LOGGER = logging.getLogger(__name__)


def register_scan_callbacks(*, app: Dash) -> None:
    """Register callbacks for submitting scans and tracking their results."""
    @app.callback(
        Output("experiment-job", "data"),
        Output("experiment-job-poll", "disabled", allow_duplicate=True),
        Output("run-experiment-button", "disabled", allow_duplicate=True),
        Output("experiment-run-status", "children", allow_duplicate=True),
        Input("run-experiment-button", "n_clicks"),
        State("source-type", "value"),
        State({"kind": "field", "section": "source", "name": ALL}, "value"),
        State({"kind": "field", "section": "source", "name": ALL}, "id"),
        State("scatterer-type", "value"),
        State({"kind": "field", "section": "scatterer", "name": ALL}, "value"),
        State({"kind": "field", "section": "scatterer", "name": ALL}, "id"),
        State("detector-type", "value"),
        State({"kind": "field", "section": "detector", "name": ALL}, "value"),
        State({"kind": "field", "section": "detector", "name": ALL}, "id"),
        State("measure-select", "value"),
        State("experiment-job", "data"),
        prevent_initial_call=True,
    )
    def _submit_experiment(
        _run_clicks: int,
        source_type: str,
        source_values: list[str],
        source_ids: list[dict[str, str]],
        scatterer_type: str,
        scatterer_values: list[str],
        scatterer_ids: list[dict[str, str]],
        detector_type: str,
        detector_values: list[str],
        detector_ids: list[dict[str, str]],
        measure: str | list[str],
        previous_job: dict | None,
    ):
        # Dynamic page insertion can invoke callbacks without a button click.
        if not _run_clicks:
            return no_update, no_update, no_update, no_update

        LOGGER.debug(
            "Preparing background parameter sweep source=%s scatterer=%s detector=%s measure=%s",
            source_type,
            scatterer_type,
            detector_type,
            measure,
        )

        source_mapping = _pair_ids_with_values(source_ids, source_values)
        scatterer_mapping = _pair_ids_with_values(scatterer_ids, scatterer_values)
        detector_mapping = _pair_ids_with_values(detector_ids, detector_values)
        try:
            request = prepare_experiment(
                source_type=source_type, source_values=source_mapping,
                scatterer_type=scatterer_type, scatterer_values=scatterer_mapping,
                detector_type=detector_type, detector_values=detector_mapping, measure=measure,
            )
            if previous_job:
                experiment_jobs.cancel(previous_job.get("job_id"))
            job_id = experiment_jobs.submit(request=request)
        except ExperimentValidationError as error:
            message = " ".join(f"{issue.field}: {issue.message}" for issue in error.issues)
            return None, True, False, status_banner("error", f"Cannot run: {message}")
        except ExperimentQueueFull as error:
            return None, True, False, status_banner("warning", str(error))
        except Exception as error:
            LOGGER.exception("Failed to queue experiment")
            return None, True, False, status_banner("error", f"Could not start the sweep: {error}. Click Run to retry.")
        inputs = [source_type, source_mapping, scatterer_type, scatterer_mapping, detector_type, detector_mapping, measure]
        return {"job_id": job_id, "inputs": inputs}, False, True, status_banner("idle", "Queued. Waiting for a computation worker…")

    @app.callback(
        Output("experiment-result", "data"),
        Output("experiment-run-count", "data"),
        Output("experiment-job-poll", "disabled"),
        Output("run-experiment-button", "disabled"),
        Output("experiment-run-status", "children"),
        Input("experiment-job-poll", "n_intervals"),
        State("experiment-job", "data"),
        State("experiment-run-count", "data"),
        prevent_initial_call=True,
    )
    def _poll_experiment_job(_n_intervals: int, job_data: dict | None, experiment_runs: int):
        snapshot = experiment_jobs.snapshot((job_data or {}).get("job_id"))
        if snapshot is None:
            message = status_banner("error", "Run interrupted: the background job is no longer available. Click Run to retry.") if job_data else no_update
            return no_update, no_update, True, False, message
        status = snapshot["status"]
        LOGGER.debug("Polling experiment job_id=%s status=%s", snapshot["job_id"], status)
        if status in {"pending", "running"}:
            message = "Queued. Waiting for a computation worker…" if status == "pending" else "Running. Computing your parameter sweep…"
            return no_update, no_update, False, True, status_banner("idle", message)
        if status == "succeeded":
            result = {**snapshot["result"], "submitted_inputs": job_data.get("inputs")}
            try:
                usage_metrics.record_experiment_run()
            except Exception:
                LOGGER.exception("Failed to record PyMieSimX experiment-run metric.")
            return result, int(experiment_runs or 0) + 1, True, False, status_banner("success", f"Completed. {result['row_count']:,} result rows.")
        if status == "cancelled":
            return no_update, no_update, True, False, status_banner("warning", "Run cancelled. Click Run to start another sweep.")
        LOGGER.warning("Experiment job failed job_id=%s error=%s", snapshot["job_id"], snapshot["error"])
        return no_update, no_update, True, False, status_banner("error", f"Run failed: {snapshot['error'] or 'An unexpected computation error occurred.'}")

    @app.callback(
        Output("experiment-stale-status", "children"),
        Input("source-type", "value"),
        Input({"kind": "field", "section": "source", "name": ALL}, "value"),
        Input("scatterer-type", "value"),
        Input({"kind": "field", "section": "scatterer", "name": ALL}, "value"),
        Input("detector-type", "value"),
        Input({"kind": "field", "section": "detector", "name": ALL}, "value"),
        Input("measure-select", "value"),
        Input("experiment-result", "data"),
        State({"kind": "field", "section": "source", "name": ALL}, "id"),
        State({"kind": "field", "section": "scatterer", "name": ALL}, "id"),
        State({"kind": "field", "section": "detector", "name": ALL}, "id"),
    )
    def _show_stale_result(source, source_values, scatterer, scatterer_values, detector, detector_values,
                           measure, result, source_ids, scatterer_ids, detector_ids):
        submitted = (result or {}).get("submitted_inputs")
        if submitted is None:
            return None
        current = [
            source, _pair_ids_with_values(source_ids, source_values),
            scatterer, _pair_ids_with_values(scatterer_ids, scatterer_values),
            detector, _pair_ids_with_values(detector_ids, detector_values), measure,
        ]
        if current != submitted:
            return status_banner("warning", "From previous run. The plot and CSV reflect the inputs used for that sweep.")
        return None
