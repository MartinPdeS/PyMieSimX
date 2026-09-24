"""Single-particle page composition."""

from dash import dcc, html

from PyMieSimX.gui.layout import PLOT_CONFIG, _plot_options_card, build_plot_options_sidebar, build_tabbed_sidebar

from .sections import build_representation_section, build_scatterer_section, build_source_section


def build_single_page(plot_settings: dict | None = None):
    """Build the single page from independent setup and plot sections."""
    return html.Div(
        className="tab-content-stack single-tab-content",
        children=[
            html.Section(
                className="single-workspace",
                children=[
                    html.Section(
                        className="result-column",
                        children=[
                            html.Div(
                                className="graph-toolbar",
                                children=[
                                    html.Button(
                                        [html.Span("\u25b6", className="toolbar-button-icon", **{"aria-hidden": "true"}), "Run"],
                                        id="run-single-button",
                                        n_clicks=0,
                                        disabled=False,
                                        className="toolbar-button toolbar-button-primary",
                                    ),
                                    html.Button(
                                        [html.Span("\u2913", className="toolbar-button-icon", **{"aria-hidden": "true"}), "Export CSV"],
                                        id="export-single-csv",
                                        n_clicks=0,
                                        disabled=True,
                                        className="toolbar-button toolbar-button-secondary",
                                    ),
                                ],
                            ),
                            html.Section(className="panel graph-panel single-graph-panel", children=[dcc.Loading(id="single-graph-loading", type="circle", color="#4f8df7", custom_spinner=html.Div("Computing…", className="plot-computing-indicator"), delay_show=150, delay_hide=150, children=dcc.Graph(id="single-graph", config=PLOT_CONFIG))]),
                            build_representation_section(),
                        ],
                    ),
                ],
            ),
            dcc.Store(id="single-right-sidebar-active", data=None),
            build_tabbed_sidebar(
                "single-right-sidebar",
                [
                    {"tab_id": "single-tab-source", "panel_id": "single-panel-source", "label": "Source", "color": "yellow", "content": build_source_section(), "active": False},
                    {"tab_id": "single-tab-scatterer", "panel_id": "single-panel-scatterer", "label": "Scatterer", "color": "blue", "content": build_scatterer_section(), "active": False},
                    {"tab_id": "single-tab-plot-options", "panel_id": "single-panel-plot-options", "label": "Plot options", "color": "purple", "content": build_plot_options_sidebar("single-plot-options-container", _plot_options_card("single", plot_settings or {})), "active": False},
                ],
            ),
        ],
    )
