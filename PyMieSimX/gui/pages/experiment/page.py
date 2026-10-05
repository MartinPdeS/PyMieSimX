"""Parameter Scan page composition."""


from dash import dcc, html

from PyMieSimX.gui.sharing import sharing_controls, sharing_feedback
from PyMieSimX.gui.components.cards import workspace_header

from PyMieSimX.gui.callback_helpers import status_banner
from PyMieSimX.gui.layout import PLOT_CONFIG, _plot_options_card, _x_axis_card, build_plot_options_sidebar, build_tabbed_sidebar

from .sections import build_detector_section, build_scatterer_section, build_source_section


def build_experiment_page(default_measure_options: list[str], plot_settings: dict | None = None, simulation: dict | None = None):
    """Build the isolated Parameter Scan workspace."""
    settings = (plot_settings or {}).get("parameter_sweep", {})
    projection = (simulation or {}).get("controls", {}).get("plot-experiment-projection", "cartesian")
    projection_options = [{"label": "Cartesian", "value": "cartesian"}, {"label": "Polar", "value": "polar"}] if projection == "polar" else None
    initial_plot_options = _plot_options_card("experiment", settings, projection=projection, projection_options=projection_options)
    return html.Div(
        className="tab-content-stack experiment-tab-content",
        children=[
            workspace_header("Compare scattering across a parameter sweep", "Run a Mie parameter sweep across source, scatterer, and detector settings. Compare scattering measures and export the results as CSV."),
            html.Section(
                id="configure",
                className="workspace",
                children=[
                    dcc.Store(id="experiment-job"),
                    dcc.Interval(id="experiment-job-poll", interval=500, n_intervals=0, disabled=True),
                    html.Section(
                        className="result-column",
                        children=[
                            html.Div(
                                className="graph-toolbar",
                                children=[
                                    html.Button(
                                        [html.Span("\u25b6", className="toolbar-button-icon", **{"aria-hidden": "true"}), "Run"],
                                        id="run-experiment-button",
                                        n_clicks=0,
                                        disabled=False,
                                        className="toolbar-button toolbar-button-primary",
                                    ),
                                    html.Button(
                                        [html.Span("\u2913", className="toolbar-button-icon", **{"aria-hidden": "true"}), "Export CSV"],
                                        id="export-csv",
                                        n_clicks=0,
                                        disabled=True,
                                        className="toolbar-button toolbar-button-secondary",
                                    ),
                                    sharing_controls("/experiment"),
                                ],
                            ),
                            html.Div(
                                id="experiment-run-status",
                                className="experiment-run-feedback",
                                children=status_banner("idle", "Ready. Click Run to start a sweep."),
                            ),
                            sharing_feedback(),
                            _x_axis_card(default_measure_options),
                            html.Section(className="panel graph-panel", children=[dcc.Loading(id="result-graph-loading", type="circle", color="#4f8df7", custom_spinner=html.Div("Computing…", className="plot-computing-indicator"), delay_show=150, delay_hide=150, children=dcc.Graph(id="result-graph", config=PLOT_CONFIG))]),
                        ],
                    ),
                ],
            ),
            dcc.Store(id="experiment-right-sidebar-active", data=None),
            build_tabbed_sidebar(
                "experiment-right-sidebar",
                [
                    {"tab_id": "experiment-tab-source", "panel_id": "experiment-panel-source", "label": "Source", "color": "yellow", "content": build_source_section(), "active": False},
                    {"tab_id": "experiment-tab-scatterer", "panel_id": "experiment-panel-scatterer", "label": "Scatterer", "color": "blue", "content": build_scatterer_section(), "active": False},
                    {"tab_id": "experiment-tab-detector", "panel_id": "experiment-panel-detector", "label": "Detector", "color": "cyan", "content": build_detector_section(), "active": False},
                    {"tab_id": "experiment-tab-plot-options", "panel_id": "experiment-panel-plot-options", "label": "Plot options", "color": "purple", "content": build_plot_options_sidebar("experiment-plot-options-container", initial_plot_options), "active": False},
                ],
            ),
        ],
    )
