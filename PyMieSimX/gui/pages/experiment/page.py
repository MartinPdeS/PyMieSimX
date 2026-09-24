"""Parameter Sweep page composition."""


from dash import dcc, html

from PyMieSimX.gui.layout import PLOT_CONFIG, _plot_options_card, _x_axis_card, build_plot_options_sidebar, build_tabbed_sidebar

from .sections import build_detector_section, build_scatterer_section, build_source_section


def build_experiment_page(default_measure_options: list[str], plot_settings: dict | None = None):
    """Build the isolated Parameter Sweep workspace."""
    settings = (plot_settings or {}).get("parameter_sweep", {})
    return html.Div(
        className="tab-content-stack experiment-tab-content",
        children=[
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
                                ],
                            ),
                            html.Section(className="panel graph-panel", children=[dcc.Loading(id="result-graph-loading", type="circle", color="#4f8df7", custom_spinner=html.Div("Computing…", className="plot-computing-indicator"), delay_show=150, delay_hide=150, children=dcc.Graph(id="result-graph", config=PLOT_CONFIG))]),
                            _x_axis_card(default_measure_options),
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
                    {"tab_id": "experiment-tab-plot-options", "panel_id": "experiment-panel-plot-options", "label": "Plot options", "color": "purple", "content": build_plot_options_sidebar("experiment-plot-options-container", _plot_options_card("experiment", settings)), "active": False},
                ],
            ),
        ],
    )
