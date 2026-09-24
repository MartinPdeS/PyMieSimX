"""Home page composition."""

from importlib.metadata import PackageNotFoundError, version

from dash import dcc, html
import numpy as np
import plotly.graph_objects as go

from PyMieSimX.gui.components import Card

def build_home_page():
    """Build the landing page and its workflow cards."""
    return html.Div(
        className="page-content-stack",
        children=[
            html.Div(
                [
                    html.Span("Version:", className="version-widget-label"),
                    html.Span(_package_version(), className="version-widget-value"),
                ],
                className="version-widget",
            ),
            html.Section(
                className="page-hero home-page-hero",
                children=[
                    html.H1("PyMieSim"),
                    html.P(
                        "An open-source library for fast and flexible far-field Mie scattering simulations.",
                        className="hero-text",
                    ),
                ],
            ),
            html.Div(
                className="home-capability-grid",
                children=[
                    _capability_card(
                        "Particle Explorer",
                        "Inspect one optical setup through angular scattering, polarization, phase functions, and field representations.",
                        ["Configure source", "Configure scatterer", "Render representations"],
                        "Open Particle Explorer",
                        "/single",
                        html.Img(src="/assets/home-spf-radial.png", className="home-capability-preview home-capability-preview-image", alt="Scattering phase function 3D radial surface"),
                        "Scattering phase function — 3D radial surface",
                        "purple",
                    ),
                    _capability_card(
                        "Parameter Sweep",
                        "Run source, scatterer, and detector configurations across parameter sweeps and export structured results for analysis.",
                        ["Configure source", "Configure scatterer and detector", "Run and export results"],
                        "Open Parameter Sweep",
                        "/experiment",
                        _qsca_preview(),
                        "Scattering-efficiency sweep",
                        "green",
                    ),
                ],
            ),
        ],
    )

def _package_version() -> str:
    try:
        return version("PyMieSimX")
    except PackageNotFoundError:
        return "development"


def _capability_card(
    title: str,
    description: str,
    steps: list[str],
    button_text: str,
    href: str,
    preview: go.Figure | html.Img,
    preview_title: str,
    color: str,
):
    preview_content = preview if isinstance(preview, html.Img) else dcc.Graph(
        figure=preview,
        config={"displayModeBar": False, "staticPlot": True, "responsive": True},
        className="home-capability-preview",
    )
    return html.Section(
        className=Card.classes(color=color, extra="home-capability-card"),
        children=[
            html.Div(title, className="home-section-header"),
            html.Div(
                className="home-capability-body",
                children=[
                    html.Div(
                        className="home-capability-content",
                        children=[
                            html.Div(
                                className="home-capability-copy",
                                children=[
                                    html.P(description),
                                    html.Div(
                                        [html.Div([html.Span(str(index), className="home-step-number"), html.Span(step)]) for index, step in enumerate(steps, start=1)],
                                        className="home-step-list",
                                    ),
                                    html.A(button_text, href=href, className="home-workflow-button"),
                                ],
                            ),
                            html.Div(
                                className="home-preview-panel",
                                children=[
                                    html.Div(preview_title, className="home-preview-title"),
                                    preview_content,
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def _preview_layout(figure: go.Figure, *, x_title: str = "", y_title: str = "") -> go.Figure:
    figure.update_layout(
        template="plotly_white",
        height=220,
        margin={"l": 48, "r": 16, "t": 12, "b": 42},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font={"size": 11, "color": "#52697a"},
        xaxis={"title": x_title, "showgrid": False, "zeroline": False},
        yaxis={"title": y_title, "gridcolor": "rgba(82,105,122,.14)", "zeroline": False},
    )
    return figure


def _qsca_preview() -> go.Figure:
    """Build an illustrative scattering-efficiency sweep preview."""
    diameter = np.linspace(80.0, 1000.0, 180)
    envelope = 2.0 * (1.0 - np.exp(-diameter / 260.0))
    resonances = 0.52 * np.sin(diameter / 54.0) * np.exp(-diameter / 900.0)
    qsca = np.clip(envelope + resonances, 0.0, None)
    figure = go.Figure(
        go.Scatter(
            x=diameter,
            y=qsca,
            mode="lines",
            line={"color": "#2672d6", "width": 3},
            fill="tozeroy",
            fillcolor="rgba(38,114,214,.10)",
            hoverinfo="skip",
        )
    )
    return _preview_layout(figure, x_title="Diameter (nm)", y_title="Qsca")
