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
                        _radial_surface_preview(),
                        "Angular scattering surface",
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
    preview: go.Figure,
    preview_title: str,
    color: str,
):
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
                                    dcc.Graph(
                                        figure=preview,
                                        config={"displayModeBar": False, "staticPlot": True, "responsive": True},
                                        className="home-capability-preview",
                                    ),
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


def _radial_surface_preview() -> go.Figure:
    """Build an illustrative 3D angular-scattering radial surface."""
    theta = np.linspace(0.0, np.pi, 52)
    phi = np.linspace(0.0, 2.0 * np.pi, 72)
    theta_grid, phi_grid = np.meshgrid(theta, phi)
    radius = np.clip(
        0.42 + 0.82 * (1.0 + np.cos(theta_grid)) ** 2 + 0.18 * np.cos(3.0 * theta_grid) ** 2,
        0.12,
        None,
    )
    radius *= 1.0 + 0.08 * np.cos(2.0 * phi_grid) * np.sin(theta_grid) ** 2
    x_values = radius * np.sin(theta_grid) * np.cos(phi_grid)
    y_values = radius * np.sin(theta_grid) * np.sin(phi_grid)
    z_values = radius * np.cos(theta_grid)
    # Normalize each display dimension independently so the directional lobe
    # remains legible inside a small cubic preview instead of collapsing into
    # a thin shape when the longest physical axis determines every range.
    def normalize_dimension(values: np.ndarray) -> np.ndarray:
        lower = float(np.min(values))
        upper = float(np.max(values))
        return 2.0 * (values - lower) / (upper - lower) - 1.0

    x_values = normalize_dimension(x_values)
    y_values = normalize_dimension(y_values)
    z_values = normalize_dimension(z_values)
    # Project the surface into 2D SVG traces. Plotly's native Surface trace
    # requires WebGL, which is commonly disabled in headless, remote, or
    # privacy-hardened browsers and would leave this preview blank.
    projected_x = 0.78 * x_values - 0.78 * y_values
    projected_y = 0.34 * x_values + 0.34 * y_values + 0.82 * z_values
    preview_extent = 1.08 * float(max(np.max(np.abs(projected_x)), np.max(np.abs(projected_y))))
    preview_range = [-preview_extent, preview_extent]
    figure = go.Figure()

    latitude_indices = range(2, theta.size - 1, 4)
    for index, theta_index in enumerate(latitude_indices):
        fraction = index / max(1, len(latitude_indices) - 1)
        figure.add_trace(
            go.Scatter(
                x=projected_x[:, theta_index],
                y=projected_y[:, theta_index],
                mode="lines",
                line={"color": f"rgba({83 + int(105 * fraction)}, {76 + int(18 * fraction)}, {190 + int(35 * fraction)}, .62)", "width": 1.2},
                hoverinfo="skip",
            )
        )

    longitude_indices = range(0, phi.size, 6)
    for index, phi_index in enumerate(longitude_indices):
        fraction = index / max(1, len(longitude_indices) - 1)
        figure.add_trace(
            go.Scatter(
                x=projected_x[phi_index, :],
                y=projected_y[phi_index, :],
                mode="lines",
                line={"color": f"rgba({64 + int(150 * fraction)}, {93 - int(25 * fraction)}, {195 + int(25 * fraction)}, .78)", "width": 1.6},
                hoverinfo="skip",
            )
        )

    figure.update_layout(
        template="plotly_white",
        height=220,
        margin={"l": 8, "r": 8, "t": 6, "b": 6},
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis={"visible": False, "range": preview_range, "fixedrange": True},
        yaxis={"visible": False, "range": preview_range, "fixedrange": True, "scaleanchor": "x", "scaleratio": 1},
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
