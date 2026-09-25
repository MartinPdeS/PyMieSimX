"""Dash callback registration for the experiment dashboard."""


import logging
from math import isfinite
from urllib.parse import parse_qs

from dash import ALL, MATCH, Dash, Input, Output, State, ctx, dcc, no_update

from PyMieSimX.gui.layout import THEME_DARK, THEME_LIGHT, build_page_with_footer, render_fields
from PyMieSimX.gui.defaults import DEFAULT_APPLICATION_SETTINGS, DEFAULT_PARTICLE_PLOT_SETTINGS, DEFAULT_SWEEP_PLOT_SETTINGS
from PyMieSimX.gui.pages.documentation import build_documentation_page
from PyMieSimX.gui.pages.sellmeier import build_sellmeier_page
from PyMieSimX.gui.pages.field_syntax import build_field_syntax_page
from PyMieSimX.gui.pages.citation import build_citation_page
from PyMieSimX.gui.pages.home import build_home_page
from PyMieSimX.gui.pages.install_local import build_install_local_page
from PyMieSimX.gui.pages.experiment import build_experiment_page
from PyMieSimX.gui.pages.settings import build_settings_page
from PyMieSimX.gui.pages.single import build_single_page
from PyMieSimX.gui.schemas import DETECTOR_FIELDS, SCATTERER_FIELDS, SINGLE_SCATTERER_FIELDS, SINGLE_SOURCE_FIELDS, SOURCE_FIELDS
from PyMieSimX.gui.callback_helpers import (
    execute_single_callback,
    merge_local_plot_values as _merge_local_plot_values,
    pair_ids_with_values as _pair_ids_with_values,
)
from PyMieSimX.gui.jobs import experiment_jobs
from PyMieSimX.gui import usage_metrics
from PyMieSimX.gui.admin import build_admin_page, collect_admin_dashboard_data, dashboard_values, is_admin_access_granted
from PyMieSimX.gui.services import (
    available_measures,
    apply_plot_settings,
    build_figure,
    export_result_to_csv,
    export_single_result_to_csv,
    infer_variable_fields,
    estimate_result_size,
    validate_experiment_inputs,
    _parse_field_value,
    _validate_positive_field,
    _is_angular_unit,
    NEARFIELD_SCATTERER_TYPES,
)


LOGGER = logging.getLogger(__name__)


def _counter(value: object) -> int:
    """Normalize browser counter state without failing on local ``NaN``."""
    try:
        numeric = float(value or 0)
    except (TypeError, ValueError):
        return 0
    return int(numeric) if isfinite(numeric) else 0


def register_callbacks(app: Dash, default_measure_options: list[str]) -> None:
    """Register all dashboard callbacks."""
    LOGGER.debug("Registering dashboard callbacks")

    @app.callback(
        Output("theme-link", "href"),
        Output("theme-store", "data"),
        Output("settings-theme-mode", "value"),
        Output("sidebar-logo", "src"),
        Input("settings-theme-mode", "value"),
        State("theme-store", "data"),
    )
    def _sync_theme(settings_theme: str | None, stored_theme: dict | None):
        theme_mode = settings_theme
        if theme_mode not in {"light", "dark"}:
            theme_mode = (stored_theme or {}).get("theme", DEFAULT_APPLICATION_SETTINGS["theme"])
        mode = "light" if theme_mode == "light" else "dark"
        logo = "/assets/pymiesim-logo.svg" if mode == "light" else "/assets/pymiesim-logo-dark.svg"
        return (THEME_LIGHT if mode == "light" else THEME_DARK), {"theme": mode}, mode, logo

    def _handle_sidebar_tabs(tab_ids: list[str], colors: list[str], current_class: str | None, current_active: str | None):
        """Shared logic: switch the active tab/panel, toggling the sidebar open if needed."""
        clicked = ctx.triggered_id
        is_open = "open" in (current_class or "").split()
        if clicked == current_active and is_open:
            new_open, new_active = False, current_active
        else:
            new_open, new_active = True, clicked
        sidebar_class = "right-sidebar-panel" + (" open" if new_open else "")
        tab_classes = [
            f"sidebar-tab sidebar-tab--{color}" + (" active" if new_open and new_active == tab_id else "")
            for tab_id, color in zip(tab_ids, colors)
        ]
        panel_styles = [{} if new_open and new_active == tab_id else {"display": "none"} for tab_id in tab_ids]
        return sidebar_class, new_active, *tab_classes, *panel_styles

    @app.callback(
        Output("single-right-sidebar", "className"),
        Output("single-right-sidebar-active", "data"),
        Output("single-tab-source", "className"),
        Output("single-tab-scatterer", "className"),
        Output("single-tab-plot-options", "className"),
        Output("single-panel-source", "style"),
        Output("single-panel-scatterer", "style"),
        Output("single-panel-plot-options", "style"),
        Input("single-tab-source", "n_clicks"),
        Input("single-tab-scatterer", "n_clicks"),
        Input("single-tab-plot-options", "n_clicks"),
        State("single-right-sidebar", "className"),
        State("single-right-sidebar-active", "data"),
        prevent_initial_call=True,
    )
    def _handle_single_sidebar_tabs(_source_clicks, _scatterer_clicks, _plot_clicks, current_class, current_active):
        tab_ids = ["single-tab-source", "single-tab-scatterer", "single-tab-plot-options"]
        return _handle_sidebar_tabs(tab_ids, ["yellow", "blue", "purple"], current_class, current_active)

    @app.callback(
        Output("experiment-right-sidebar", "className"),
        Output("experiment-right-sidebar-active", "data"),
        Output("experiment-tab-source", "className"),
        Output("experiment-tab-scatterer", "className"),
        Output("experiment-tab-detector", "className"),
        Output("experiment-tab-plot-options", "className"),
        Output("experiment-panel-source", "style"),
        Output("experiment-panel-scatterer", "style"),
        Output("experiment-panel-detector", "style"),
        Output("experiment-panel-plot-options", "style"),
        Input("experiment-tab-source", "n_clicks"),
        Input("experiment-tab-scatterer", "n_clicks"),
        Input("experiment-tab-detector", "n_clicks"),
        Input("experiment-tab-plot-options", "n_clicks"),
        State("experiment-right-sidebar", "className"),
        State("experiment-right-sidebar-active", "data"),
        prevent_initial_call=True,
    )
    def _handle_experiment_sidebar_tabs(_source_clicks, _scatterer_clicks, _detector_clicks, _plot_clicks, current_class, current_active):
        tab_ids = ["experiment-tab-source", "experiment-tab-scatterer", "experiment-tab-detector", "experiment-tab-plot-options"]
        return _handle_sidebar_tabs(tab_ids, ["yellow", "blue", "cyan", "purple"], current_class, current_active)


    @app.callback(
        Output("page-content", "children"),
        Output("sidebar-link-home", "className"),
        Output("sidebar-link-experiment", "className"),
        Output("sidebar-link-single", "className"),
        Output("sidebar-link-documentation", "className"),
        Output("sidebar-link-settings", "className"),
        Output("home-visit-count", "data"),
        Input("url", "pathname"),
        Input("url", "search"),
        State("home-visit-count", "data"),
        State("experiment-run-count", "data"),
        State("single-run-count", "data"),
        State("theme-store", "data"),
        State("plot-settings-store", "data"),
    )
    def _route_pages(pathname: str | None, search: str | None, home_visits: int, experiment_runs: int, single_runs: int, theme_store: dict | None, plot_settings: dict | None):
        """Render only the selected route page inside the persistent shell."""
        route = pathname or "/"
        active = {
            "home": "sidebar-link",
            "experiment": "sidebar-link",
            "single": "sidebar-link",
            "documentation": "sidebar-link",
            "settings": "sidebar-link",
        }
        home_visits = _counter(home_visits)
        if route == "/":
            try:
                server_metrics = usage_metrics.record_home_page_visit()
                home_visits = server_metrics.home_page_visit_count
            except Exception:
                LOGGER.exception("Failed to record PyMieSimX home-page visit metric.")
                home_visits = float("nan")
        if route == "/admin":
            token = parse_qs((search or "").lstrip("?")).get("token", [None])[0]
            return build_page_with_footer(build_admin_page(token)), *(active[key] for key in ("home", "experiment", "single", "documentation", "settings")), home_visits
        if route == "/documentation":
            active["documentation"] += " active"
            return build_page_with_footer(build_documentation_page()), *(active[key] for key in ("home", "experiment", "single", "documentation", "settings")), home_visits
        if route == "/citation":
            active["home"] += " active"
            return build_page_with_footer(build_citation_page()), *(active[key] for key in ("home", "experiment", "single", "documentation", "settings")), home_visits
        if route == "/documentation/install-local":
            active["documentation"] += " active"
            return build_page_with_footer(build_install_local_page()), *(active[key] for key in ("home", "experiment", "single", "documentation", "settings")), home_visits
        if route == "/documentation/sellmeier":
            active["documentation"] += " active"
            return build_page_with_footer(build_sellmeier_page()), *(active[key] for key in ("home", "experiment", "single", "documentation", "settings")), home_visits
        if route == "/documentation/field-syntax":
            active["documentation"] += " active"
            return build_page_with_footer(build_field_syntax_page()), *(active[key] for key in ("home", "experiment", "single", "documentation", "settings")), home_visits
        if route == "/settings":
            active["settings"] += " active"
            return build_page_with_footer(build_settings_page((theme_store or {}).get("theme", "light"), plot_settings or {})), *(active[key] for key in ("home", "experiment", "single", "documentation", "settings")), home_visits
        if route == "/single":
            active["single"] += " active"
            return build_page_with_footer(build_single_page((plot_settings or {}).get("particle_explorer", {}))), *(active[key] for key in ("home", "experiment", "single", "documentation", "settings")), home_visits
        if route == "/experiment":
            active["experiment"] += " active"
            return build_page_with_footer(build_experiment_page(default_measure_options, plot_settings or {})), *(active[key] for key in ("home", "experiment", "single", "documentation", "settings")), home_visits
        active["home"] += " active"
        return build_page_with_footer(build_home_page()), *(active[key] for key in ("home", "experiment", "single", "documentation", "settings")), home_visits

    @app.callback(
        Output("admin-home-page-visits", "children"),
        Output("admin-experiment-runs", "children"),
        Output("admin-single-runs", "children"),
        Output("admin-last-updated", "children"),
        Input("admin-refresh-interval", "n_intervals"),
        Input("admin-refresh-button", "n_clicks"),
        State("url", "search"),
        prevent_initial_call=False,
    )
    def _refresh_admin_dashboard(_n_intervals: int, _n_clicks: int, search: str | None):
        token = parse_qs((search or "").lstrip("?")).get("token", [None])[0]
        if not is_admin_access_granted(token):
            return no_update, no_update, no_update, no_update
        return dashboard_values(collect_admin_dashboard_data())

    @app.callback(
        Output("plot-settings-store", "data"),
        Input("settings-particle-font-size", "value", allow_optional=True),
        Input("settings-particle-line-width", "value", allow_optional=True),
        Input("settings-particle-graph-height", "value", allow_optional=True),
        Input("settings-particle-template", "value", allow_optional=True),
        Input("settings-particle-coordinates", "value", allow_optional=True),
        Input("settings-particle-x-scale", "value", allow_optional=True),
        Input("settings-particle-legend", "value", allow_optional=True),
        Input("settings-particle-grid", "value", allow_optional=True),
        Input("settings-particle-log-y", "value", allow_optional=True),
        Input("settings-sweep-font-size", "value", allow_optional=True),
        Input("settings-sweep-line-width", "value", allow_optional=True),
        Input("settings-sweep-graph-height", "value", allow_optional=True),
        Input("settings-sweep-template", "value", allow_optional=True),
        Input("settings-sweep-coordinates", "value", allow_optional=True),
        Input("settings-sweep-x-scale", "value", allow_optional=True),
        Input("settings-sweep-legend", "value", allow_optional=True),
        Input("settings-sweep-grid", "value", allow_optional=True),
        Input("settings-sweep-log-y", "value", allow_optional=True),
        Input("plot-single-x-scale", "value", allow_optional=True),
        Input("plot-single-y-scale", "value", allow_optional=True),
        Input("plot-single-font-size", "value", allow_optional=True),
        Input("plot-single-line-width", "value", allow_optional=True),
        Input("plot-single-legend", "value", allow_optional=True),
        Input("plot-single-grid", "value", allow_optional=True),
        Input("plot-experiment-x-scale", "value", allow_optional=True),
        Input("plot-experiment-y-scale", "value", allow_optional=True),
        Input("plot-experiment-font-size", "value", allow_optional=True),
        Input("plot-experiment-line-width", "value", allow_optional=True),
        Input("plot-experiment-legend", "value", allow_optional=True),
        Input("plot-experiment-grid", "value", allow_optional=True),
        State("plot-settings-store", "data"),
    )
    def _sync_plot_settings(*values):
        stored_settings = values[-1] or {}
        particle_values = values[:9]
        sweep_values = values[9:18]
        single_local_values = values[18:24]
        experiment_local_values = values[24:30]

        def merge(defaults, key, settings_values):
            current = {**defaults, **(stored_settings.get(key, {}) if isinstance(stored_settings, dict) else {})}
            names = ("font_size", "line_width", "graph_height", "template", "coordinate_system", "x_scale", "show_legend", "show_grid", "log_y")
            for name, value in zip(names, settings_values):
                if value is not None:
                    current[name] = value
            return current

        def merge_local(current, local_values):
            names = ("x_scale", "log_y", "font_size", "line_width", "show_legend", "show_grid")
            for name, value in zip(names, local_values):
                if value is not None:
                    current[name] = value
            return current

        particle = merge(DEFAULT_PARTICLE_PLOT_SETTINGS, "particle_explorer", particle_values)
        sweep = merge(DEFAULT_SWEEP_PLOT_SETTINGS, "parameter_sweep", sweep_values)
        return {
            "particle_explorer": merge_local(particle, single_local_values),
            "parameter_sweep": merge_local(sweep, experiment_local_values),
        }

    @app.callback(
        Output({"kind": "field", "section": MATCH, "name": ALL}, "className"),
        Output({"kind": "field-error", "section": MATCH, "name": ALL}, "children"),
        Input({"kind": "field", "section": MATCH, "name": ALL}, "value"),
        State({"kind": "field", "section": MATCH, "name": ALL}, "id"),
        State("source-type", "value", allow_optional=True),
        State("scatterer-type", "value", allow_optional=True),
        State("detector-type", "value", allow_optional=True),
        State("single-source-type", "value", allow_optional=True),
        State("single-scatterer-type", "value", allow_optional=True),
    )
    def _validate_fields(values, field_ids, source_type, scatterer_type, detector_type, single_source_type, single_scatterer_type):
        """Mark schema-invalid dynamic inputs and surface an inline error message, without interrupting the form."""
        if not field_ids:
            return [], []

        selected_types = {
            "source": source_type,
            "scatterer": scatterer_type,
            "detector": detector_type,
            "single-source": single_source_type,
            "single-scatterer": single_scatterer_type,
        }
        schema_groups = {
            "source": SOURCE_FIELDS,
            "scatterer": SCATTERER_FIELDS,
            "detector": DETECTOR_FIELDS,
            "single-source": SINGLE_SOURCE_FIELDS,
            "single-scatterer": SINGLE_SCATTERER_FIELDS,
        }

        classes = []
        errors = []
        for field_id, raw_value in zip(field_ids, values):
            section = field_id["section"]
            selected_type = selected_types.get(section)
            field_specs = schema_groups.get(section, {}).get(selected_type, ())
            field = next((spec for spec in field_specs if spec.name == field_id["name"]), None)
            valid = field is not None
            error_message = ""

            if field is not None:
                empty = raw_value is None or str(raw_value).strip() == ""
                valid = field.optional and empty
                if not empty:
                    try:
                        parsed_value = _parse_field_value(field.kind, raw_value, field.unit)
                        if field.name in {"wavelength", "optical_power", "numerical_aperture", "amplitude", "diameter", "core_diameter", "shell_thickness", "sampling"}:
                            _validate_positive_field(field.name, parsed_value)
                        valid = True
                    except (TypeError, ValueError, KeyError) as error:
                        valid = False
                        error_message = str(error)
                elif not field.optional:
                    error_message = "A value is required."

            is_detector_default = section == "detector" and field is not None and field.name in {"polarization_filter", "medium"} and (raw_value is None or str(raw_value).strip() in {"", field.default})
            classes.append("field-input field-input-default" if valid and is_detector_default else "field-input" if valid else "field-input field-input-invalid")
            errors.append(error_message)

        return classes, errors

    @app.callback(Output("source-fields", "children"), Input("source-type", "value"))
    def _render_source_fields(source_type: str):
        LOGGER.debug("Rendering source fields for %s", source_type)
        return render_fields("source", source_type)

    @app.callback(Output("scatterer-fields", "children"), Input("scatterer-type", "value"))
    def _render_scatterer_fields(scatterer_type: str):
        LOGGER.debug("Rendering scatterer fields for %s", scatterer_type)
        return render_fields("scatterer", scatterer_type)

    @app.callback(Output("detector-fields", "children"), Input("detector-type", "value"))
    def _render_detector_fields(detector_type: str):
        LOGGER.debug("Rendering detector fields for %s", detector_type)
        return render_fields("detector", detector_type)

    @app.callback(Output("single-source-fields", "children"), Input("single-source-type", "value"))
    def _render_single_source_fields(source_type: str):
        return render_fields("single-source", source_type)

    @app.callback(Output("single-scatterer-fields", "children"), Input("single-scatterer-type", "value"))
    def _render_single_scatterer_fields(scatterer_type: str):
        return render_fields("single-scatterer", scatterer_type)

    @app.callback(
        Output({"kind": "material-toggle", "section": MATCH, "name": MATCH}, "className"),
        Output({"kind": "material-ri-input-wrapper", "section": MATCH, "name": MATCH}, "style"),
        Output({"kind": "material-dropdown-wrapper", "section": MATCH, "name": MATCH}, "style"),
        Output({"kind": "field", "section": MATCH, "name": MATCH}, "value"),
        Output({"kind": "material-ri-value", "section": MATCH, "name": MATCH}, "data"),
        Input({"kind": "material-toggle", "section": MATCH, "name": MATCH}, "n_clicks"),
        Input({"kind": "material-select", "section": MATCH, "name": MATCH}, "value"),
        State({"kind": "field", "section": MATCH, "name": MATCH}, "value"),
        State({"kind": "material-ri-value", "section": MATCH, "name": MATCH}, "data"),
    )
    def _sync_material_field_mode(
        toggle_clicks: int | None,
        selected_material: str | None,
        current_value: str | None,
        stored_ri_value: str | None,
    ):
        """Toggle between RI text input and named-material dropdown."""
        use_named_material = bool((toggle_clicks or 0) % 2)
        toggle_class = "material-mode-toggle is-material" if use_named_material else "material-mode-toggle is-index"
        ri_style = {"display": "none"} if use_named_material else {}
        dropdown_style = {} if use_named_material else {"display": "none"}
        ri_value = stored_ri_value or "1.4"

        if current_value and not any(char.isalpha() for char in str(current_value)):
            ri_value = current_value

        if use_named_material and selected_material:
            return toggle_class, ri_style, dropdown_style, selected_material, ri_value

        return toggle_class, ri_style, dropdown_style, ri_value, ri_value

    @app.callback(
        Output("measure-select", "options"),
        Output("measure-select", "value"),
        Output("detector-coupling-alert", "style"),
        Input("scatterer-type", "value"),
        Input("detector-type", "value"),
        State("measure-select", "value"),
    )
    def _update_measure_options(scatterer_type: str, detector_type: str, current_measure: str | None):
        LOGGER.debug(
            "Updating measure options for scatterer=%s detector=%s current=%s",
            scatterer_type,
            detector_type,
            current_measure,
        )
        measures = available_measures(scatterer_type, detector_type)
        options = [{"label": measure, "value": measure} for measure in measures]
        value = current_measure if current_measure in measures else measures[0]
        alert_style = {} if detector_type == "None" else {"display": "none"}
        return options, value, alert_style

    @app.callback(
        Output("x-axis-select", "options"),
        Output("x-axis-select", "value"),
        Input("source-type", "value"),
        Input({"kind": "field", "section": "source", "name": ALL}, "value"),
        Input({"kind": "field", "section": "source", "name": ALL}, "id"),
        Input("scatterer-type", "value"),
        Input({"kind": "field", "section": "scatterer", "name": ALL}, "value"),
        Input({"kind": "field", "section": "scatterer", "name": ALL}, "id"),
        Input("detector-type", "value"),
        Input({"kind": "field", "section": "detector", "name": ALL}, "value"),
        Input({"kind": "field", "section": "detector", "name": ALL}, "id"),
        State("x-axis-select", "value"),
    )
    def _update_x_axis_options(
        source_type: str,
        source_values: list[str],
        source_ids: list[dict[str, str]],
        scatterer_type: str,
        scatterer_values: list[str],
        scatterer_ids: list[dict[str, str]],
        detector_type: str,
        detector_values: list[str],
        detector_ids: list[dict[str, str]],
        current_x_axis: str | None,
    ):
        LOGGER.debug(
            "Updating x-axis options from form state source=%s scatterer=%s detector=%s current=%s",
            source_type,
            scatterer_type,
            detector_type,
            current_x_axis,
        )

        variable_fields = infer_variable_fields(
            source_type=source_type,
            source_values=_pair_ids_with_values(source_ids, source_values),
            scatterer_type=scatterer_type,
            scatterer_values=_pair_ids_with_values(scatterer_ids, scatterer_values),
            detector_type=detector_type,
            detector_values=_pair_ids_with_values(detector_ids, detector_values),
        )

        options = [{"label": field_name, "value": field_name} for field_name in variable_fields]
        value = current_x_axis if current_x_axis in variable_fields else (variable_fields[0] if variable_fields else None)
        return options, value

    @app.callback(
        Output("experiment-job", "data"),
        Output("experiment-job-poll", "disabled", allow_duplicate=True),
        Output("run-experiment-button", "disabled", allow_duplicate=True),
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
        prevent_initial_call="initial_duplicate",
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
        measure: str,
        previous_job: dict | None,
    ):
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
        issues = validate_experiment_inputs(
            source_type=source_type,
            source_values=source_mapping,
            scatterer_type=scatterer_type,
            scatterer_values=scatterer_mapping,
            detector_type=detector_type,
            detector_values=detector_mapping,
            measure=measure,
        )
        if issues:
            message = " ".join(issue.message for issue in issues)
            LOGGER.info("Experiment submission rejected: %s", message)
            return None, True, False

        if previous_job:
            experiment_jobs.cancel(previous_job.get("job_id"))
        estimate = estimate_result_size(
            source_type=source_type,
            source_values=source_mapping,
            scatterer_type=scatterer_type,
            scatterer_values=scatterer_mapping,
            detector_type=detector_type,
            detector_values=detector_mapping,
        )
        job_id = experiment_jobs.submit(
            source_type=source_type,
            source_values=source_mapping,
            scatterer_type=scatterer_type,
            scatterer_values=scatterer_mapping,
            detector_type=detector_type,
            detector_values=detector_mapping,
            measure=measure,
        )
        LOGGER.info("Experiment queued job_id=%s rows_estimate=%d bytes_estimate=%d", job_id, estimate.rows, estimate.estimated_bytes)
        return {"job_id": job_id}, False, True

    @app.callback(
        Output("experiment-result", "data"),
        Output("experiment-run-count", "data"),
        Output("experiment-job-poll", "disabled"),
        Output("run-experiment-button", "disabled"),
        Input("experiment-job-poll", "n_intervals"),
        State("experiment-job", "data"),
        State("experiment-run-count", "data"),
        prevent_initial_call=True,
    )
    def _poll_experiment_job(_n_intervals: int, job_data: dict | None, experiment_runs: int):
        snapshot = experiment_jobs.snapshot((job_data or {}).get("job_id"))
        if snapshot is None:
            return no_update, no_update, True, no_update
        status = snapshot["status"]
        LOGGER.debug("Polling experiment job_id=%s status=%s", snapshot["job_id"], status)
        if status in {"pending", "running"}:
            return no_update, no_update, False, no_update
        if status == "succeeded":
            result = snapshot["result"]
            try:
                usage_metrics.record_experiment_run()
            except Exception:
                LOGGER.exception("Failed to record PyMieSimX experiment-run metric.")
            return result, int(experiment_runs or 0) + 1, True, False
        LOGGER.warning("Experiment job failed job_id=%s error=%s", snapshot["job_id"], snapshot["error"])
        return no_update, no_update, True, False

    @app.callback(
        Output("csv-download", "data"),
        Input("export-csv", "n_clicks"),
        State("experiment-result", "data"),
        State("measure-select", "value"),
        prevent_initial_call=True,
    )
    def _export_csv(n_clicks: int, result: dict | None, measure: str | None):
        LOGGER.debug("CSV export requested for measure=%s", measure)

        if not n_clicks:
            LOGGER.debug("Ignoring CSV callback without an explicit button click")
            return no_update

        csv_content = export_result_to_csv(result)

        if not csv_content:
            LOGGER.debug("No CSV exported because result content is empty")
            return no_update

        filename = f"pymiesim_{measure or 'result'}.csv"
        LOGGER.debug("CSV export generated filename=%s", filename)
        return dcc.send_string(csv_content, filename)

    @app.callback(
        Output("single-csv-download", "data"),
        Input("export-single-csv", "n_clicks"),
        State("single-result", "data"),
        prevent_initial_call=True,
    )
    def _export_single_csv(n_clicks: int, result: dict | None):
        if not n_clicks:
            return no_update

        csv_content = export_single_result_to_csv(result)
        if not csv_content:
            return no_update

        return dcc.send_string(csv_content, "pymiesim_particle_explorer.csv")

    @app.callback(
        Output("result-graph", "figure"),
        Input("experiment-result", "data"),
        Input("x-axis-select", "value"),
        Input("plot-settings-store", "data"),
        Input("theme-store", "data"),
        Input("plot-experiment-x-scale", "value", allow_optional=True),
        Input("plot-experiment-y-scale", "value", allow_optional=True),
        Input("plot-experiment-font-size", "value", allow_optional=True),
        Input("plot-experiment-line-width", "value", allow_optional=True),
        Input("plot-experiment-legend", "value", allow_optional=True),
        Input("plot-experiment-grid", "value", allow_optional=True),
        Input("plot-experiment-projection", "value", allow_optional=True),
    )
    def _update_outputs(result: dict | None, x_axis: str | None, plot_settings: dict | None, theme_store: dict | None, *local_values):
        LOGGER.debug("Updating outputs for x_axis=%s result_present=%s", x_axis, bool(result))
        projection = local_values[-1] or "cartesian"
        sweep_settings = (plot_settings or {}).get("parameter_sweep", plot_settings or {})
        sweep_settings = _merge_local_plot_values(sweep_settings, local_values[:-1])
        return build_figure(result, x_axis, plot_settings=sweep_settings, theme=(theme_store or {}).get("theme", "light"), projection=projection)

    @app.callback(
        Output("export-csv", "disabled"),
        Input("experiment-result", "data"),
    )
    def _toggle_experiment_export(result: dict | None):
        """Keep Export CSV greyed out until a sweep has actually run."""
        return not result

    @app.callback(
        Output("single-result", "data"),
        Output("single-run-count", "data"),
        Input("run-single-button", "n_clicks"),
        Input("single-projection", "value"),
        State("single-source-type", "value"),
        State({"kind": "field", "section": "single-source", "name": ALL}, "value"),
        State({"kind": "field", "section": "single-source", "name": ALL}, "id"),
        State("single-scatterer-type", "value"),
        State({"kind": "field", "section": "single-scatterer", "name": ALL}, "value"),
        State({"kind": "field", "section": "single-scatterer", "name": ALL}, "id"),
        State("single-representation", "value"),
        State("single-sampling", "value"),
        State("single-nearfield-mode", "value"),
        State("single-include-incident-field", "value"),
        State("single-run-count", "data"),
    )
    def _run_single(
        _run_clicks: int,
        projection: str,
        source_type: str,
        source_values: list[str],
        source_ids: list[dict[str, str]],
        scatterer_type: str,
        scatterer_values: list[str],
        scatterer_ids: list[dict[str, str]],
        representation: str,
        sampling: int,
        nearfield_mode: list[str] | str | None,
        include_incident_field: list[str] | None,
        single_runs: int,
    ):
        execution = execute_single_callback(
            source_type=source_type,
            source_values=source_values,
            source_ids=source_ids,
            scatterer_type=scatterer_type,
            scatterer_values=scatterer_values,
            scatterer_ids=scatterer_ids,
            representation=representation,
            projection=projection,
            sampling=sampling or 120,
            nearfield_mode=nearfield_mode,
            include_incident_field=include_incident_field,
            run_count=single_runs,
        )
        if execution.level == "error":
            LOGGER.info("Single representation render failed: %s", execution.message)
            return None, execution.run_count
        try:
            usage_metrics.record_single_run()
        except Exception:
            LOGGER.exception("Failed to record PyMieSimX particle-explorer metric.")
        return execution.result, execution.run_count

    @app.callback(
        Output("single-representation", "options"),
        Output("single-representation", "value"),
        Output("single-nearfield-availability-alert", "style"),
        Output("single-nearfield-availability-alert", "children"),
        Input("single-scatterer-type", "value"),
        State("single-representation", "value"),
    )
    def _update_single_representation_options(scatterer_type: str, current_representation: str | None):
        nearfield_supported = scatterer_type in NEARFIELD_SCATTERER_TYPES
        nearfield_values = {"nearfields", "nearfields_ex", "nearfields_ey", "nearfields_ez"}
        options = [
            {"label": "S1 / S2 amplitudes", "value": "s1s2"},
            {"label": "Stokes I intensity", "value": "stokes"},
            {"label": "Stokes Q", "value": "stokes_q"},
            {"label": "Stokes U", "value": "stokes_u"},
            {"label": "Stokes V", "value": "stokes_v"},
            {"label": "Scattering phase function", "value": "spf"},
            {"label": "Far-field intensity", "value": "farfields"},
            {"label": "Near-field |E|", "value": "nearfields", "disabled": not nearfield_supported},
            {"label": "Near-field Ex", "value": "nearfields_ex", "disabled": not nearfield_supported},
            {"label": "Near-field Ey", "value": "nearfields_ey", "disabled": not nearfield_supported},
            {"label": "Near-field Ez", "value": "nearfields_ez", "disabled": not nearfield_supported},
        ]
        value = current_representation if current_representation and (nearfield_supported or current_representation not in nearfield_values) else "s1s2"
        alert_style = {"display": "none"} if nearfield_supported else {"display": "block"}
        alert = "Near-field calculations are unavailable for the selected particle type."
        return options, value, alert_style, alert

    @app.callback(
        Output("single-projection", "options"),
        Output("single-projection", "value"),
        Output("single-nearfield-mode-field", "style"),
        Output("single-nearfield-incident-field", "style"),
        Output("single-nearfield-controls-row", "style"),
        Input("single-representation", "value"),
        State("single-projection", "value"),
    )
    def _update_single_projection_options(representation: str, current_projection: str | None):
        if representation == "s1s2":
            options = [{"label": "2D plot", "value": "2d"}, {"label": "Polar 1D", "value": "polar_1d"}]
            hidden = {"display": "none"}
            return options, current_projection if current_projection == "polar_1d" else "2d", hidden, hidden, hidden

        supports_3d = representation in {"stokes", "stokes_q", "stokes_u", "stokes_v", "spf", "farfields"}
        supports_heatmap = supports_3d or str(representation or "").startswith("nearfields")
        options = [{"label": "2D heatmap" if supports_heatmap else "2D plot", "value": "2d"}]
        if supports_3d:
            options.extend([
                {"label": "3D sphere", "value": "3d"},
                {"label": "3D radial surface", "value": "3d_radial"},
            ])
        is_nearfield = str(representation or "").startswith("nearfields")
        nearfield_style = {"display": "block" if is_nearfield else "none"}
        return options, current_projection if supports_3d and current_projection in {"3d", "3d_radial"} else "2d", nearfield_style, nearfield_style, nearfield_style

    @app.callback(
        Output("single-plot-options-container", "children"),
        Input("single-representation", "value"),
        Input("single-projection", "value"),
        State("plot-settings-store", "data"),
    )
    def _update_single_plot_options(representation: str, projection: str, plot_settings: dict | None):
        particle_settings = (plot_settings or {}).get("particle_explorer", plot_settings or {})
        from PyMieSimX.gui.layout import _plot_options_card

        return _plot_options_card("single", particle_settings, representation, projection)

    @app.callback(
        Output("experiment-plot-options-container", "children"),
        Input("x-axis-select", "value"),
        Input("experiment-result", "data"),
        State("plot-settings-store", "data"),
        State("plot-experiment-projection", "value", allow_optional=True),
    )
    def _update_experiment_plot_options(x_axis: str | None, result: dict | None, plot_settings: dict | None, current_projection: str | None):
        sweep_settings = (plot_settings or {}).get("parameter_sweep", plot_settings or {})
        units = (result or {}).get("units", {})
        xaxis_unit = units.get(x_axis)
        if xaxis_unit is None and x_axis:
            matching_units = [value for key, value in units.items() if key.rsplit(":", 1)[-1] == x_axis]
            xaxis_unit = matching_units[0] if matching_units else None
        is_angle = _is_angular_unit(xaxis_unit)
        options = [{"label": "Cartesian", "value": "cartesian"}]
        if is_angle:
            options.append({"label": "Polar", "value": "polar"})
        projection = current_projection if is_angle and current_projection == "polar" else "cartesian"
        from PyMieSimX.gui.layout import _plot_options_card

        return _plot_options_card("experiment", sweep_settings, projection=projection, projection_options=options)

    @app.callback(
        Output("single-graph", "figure"),
        Input("single-result", "data"),
        Input("plot-settings-store", "data"),
        Input("theme-store", "data"),
        Input("plot-single-x-scale", "value", allow_optional=True),
        Input("plot-single-y-scale", "value", allow_optional=True),
        Input("plot-single-font-size", "value", allow_optional=True),
        Input("plot-single-line-width", "value", allow_optional=True),
        Input("plot-single-legend", "value", allow_optional=True),
        Input("plot-single-grid", "value", allow_optional=True),
    )
    def _update_single_outputs(result: dict | None, plot_settings: dict | None, theme_store: dict | None, *local_values):
        particle_settings = (plot_settings or {}).get("particle_explorer", plot_settings or {})
        particle_settings = _merge_local_plot_values(particle_settings, local_values)
        if not result:
            return build_single_empty_figure(plot_settings=particle_settings, theme=(theme_store or {}).get("theme", "light"))
        from plotly.graph_objects import Figure

        return apply_plot_settings(Figure(result["figure"]), particle_settings, (theme_store or {}).get("theme", "light"))

    @app.callback(
        Output("export-single-csv", "disabled"),
        Input("single-result", "data"),
    )
    def _toggle_single_actions(result: dict | None):
        """Keep Export CSV greyed out until Run has produced a result."""
        return not result


def build_single_empty_figure(plot_settings: dict | None = None, theme: str = "light"):
    """Return the initial representation canvas."""
    from plotly.graph_objects import Figure

    figure = Figure()
    figure.update_layout(template="plotly_white", xaxis_visible=False, yaxis_visible=False, annotations=[{"text": "Configure a setup to inspect a representation.", "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5, "showarrow": False}])
    return apply_plot_settings(figure, plot_settings, theme)


__all__ = ["build_single_empty_figure", "register_callbacks"]
