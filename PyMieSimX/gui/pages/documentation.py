"""Documentation hub page composition."""

from dash import html

from PyMieSimX.gui.components import Card


def build_documentation_page():
    """Build the in-app guide to PyMieSim workflows and vocabulary."""
    return html.Div(
        className="page-content-stack documentation-page",
        children=[
            html.Section(
                className="page-hero documentation-page-hero",
                children=[
                    html.P("PyMieSim reference", className="eyebrow"),
                    html.H1("Documentation"),
                    html.P("A practical guide to building optical setups, running sweeps, reading representations, and entering values efficiently.", className="hero-text"),
                    html.Div(
                        className="documentation-hero-actions",
                        children=[
                            html.A("Start a parameter sweep →", href="/experiment", className="home-button home-button-primary"),
                            html.A("Open Particle Explorer →", href="/single", className="home-button home-button-outline"),
                        ],
                    ),
                ],
            ),
            html.Section(
                className=Card.classes(color="blue", extra="panel documentation-quickstart"),
                children=[
                    html.Div(className="card-header panel-header", children=[html.H2("Quick start")]),
                    html.Div(
                        className="card-body documentation-quickstart-body",
                        children=[
                            _step("01", "Choose a workspace", "Use Parameter Sweep for parameter sweeps and detector coupling. Use Particle Explorer to inspect one optical setup."),
                            _step("02", "Configure the objects", "Pick a source, scatterer, and—when needed—a detector. Each card exposes the fields supported by that model."),
                            _step("03", "Enter values or sweeps", "Use one value for a focused run, a comma-separated list for selected values, or start:end:count for an evenly spaced sweep."),
                            _step("04", "Render and inspect", "Run the calculation, select the X axis when several fields vary, and use Settings to tune the resulting plots."),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="documentation-grid documentation-topic-grid",
                children=[
                    _guide_card("yellow", "Parameter Sweep", "Sweep a parameter space", "Build source, scatterer, and detector sets, then evaluate a measure over every combination.", ["X-axis is inferred from fields with multiple values.", "Detector-free runs are supported.", "Results can be exported as CSV."], "/experiment", "Open Parameter Sweep"),
                    _guide_card("blue", "Particle Explorer", "Understand one setup", "Inspect angular amplitudes, polarization, phase functions, or far-field intensity for one source and scatterer.", ["Choose a representation.", "Control angular sampling.", "Render the figure on demand."], "/single", "Open Particle Explorer"),
                    _guide_card("green", "Material model", "Sellmeier relation", "Understand dispersive refractive-index modeling and check the coefficient table used for material workflows.", ["See the Sellmeier equation.", "Review coefficient values.", "Map values to material inputs."], "/documentation/sellmeier", "Open Sellmeier reference"),
                    _guide_card("blue", "Input reference", "Field syntax & vocabulary", "Learn compact field notation, detector definitions, and the model terms used throughout the dashboard.", ["Enter scalars, lists, and ranges.", "Understand detector choices.", "Review supported model families."], "/documentation/field-syntax", "Open field reference"),
                    _guide_card("cyan", "Plot settings", "Make figures your own", "Set typography, line and marker sizes, grid visibility, legend visibility, and light or dark plot styling.", ["Preferences are saved in this browser.", "Settings apply to both workspaces.", "The application theme is controlled here."], "/settings", "Open Settings"),
                    _guide_card("purple", "Citation", "Reference the project", "Find the publication details and ready-to-copy BibTeX entry for work that uses PyMieSim.", ["Publication DOI is included.", "BibTeX is formatted for direct copying.", "Citation guidance is kept with the reference."], "/citation", "View Citation"),
                ],
            ),
            html.Section(
                className=Card.classes(color="blue", extra="panel documentation-note"),
                children=[
                    html.Div(className="card-header panel-header", children=[html.H2("Need more detail?")]),
                    html.Div(className="card-body documentation-note-body", children=[html.P("The dashboard is designed to keep the common path visible: configure an object, run a calculation, then refine the plot. For local installation instructions and release links, open the installation guide."), html.A("Open installation guide →", href="/documentation/install-local", className="inline-action")]),
                ],
            ),
        ],
    )

def _step(number: str, title: str, description: str):
    return html.Div(className="documentation-step", children=[html.Span(number, className="documentation-step-number"), html.Div([html.H3(title), html.P(description)])])


def _guide_card(color: str, eyebrow: str, title: str, description: str, bullets: list[str], href: str, action: str):
    return html.Section(
        className=Card.classes(color=color, extra="panel documentation-guide-card"),
        children=[
            html.Div(className="card-header panel-header", children=[html.Span(eyebrow, className="documentation-card-kicker"), html.H2(title)]),
            html.Div(className="card-body", children=[html.P(description), html.Ul([html.Li(item) for item in bullets], className="documentation-bullet-list"), html.A(f"{action} →", href=href, className="inline-action")]),
        ],
    )
