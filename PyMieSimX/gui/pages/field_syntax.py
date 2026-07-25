"""Field syntax, detector definitions, and core vocabulary documentation."""

from dash import html

from PyMieSimX.gui.components import Card


def build_field_syntax_page():
    """Build the reference page for entering values and choosing detectors."""
    return html.Div(
        className="page-content-stack documentation-page",
        children=[
            html.Section(
                className="page-hero documentation-page-hero",
                children=[
                    html.P("PyMieSim reference", className="eyebrow"),
                    html.H1("Field Syntax & Vocabulary"),
                    html.P("Learn how to enter values, define detector models, and interpret the language used throughout the dashboard.", className="hero-text"),
                ],
            ),
            html.Div(className="documentation-columns", children=[_syntax_card(), _vocabulary_card()]),
            _detector_definitions_card(),
            html.Section(
                className=Card.classes(color="green", extra="panel documentation-models"),
                children=[
                    html.Div(className="card-header panel-header", children=[html.H2("Supported model families")]),
                    html.Div(
                        className="card-body documentation-model-grid",
                        children=[
                            _model_group("Sources", "Gaussian", "Plane wave"),
                            _model_group("Scatterers", "Sphere", "Infinite cylinder", "Core-shell"),
                            _model_group("Detectors", "Photodiode", "Coherent mode", "No detector"),
                            _model_group("Representations", "S1 / S2", "Stokes", "SPF", "Far-field"),
                        ],
                    ),
                ],
            ),
            html.Section(
                className=Card.classes(color="blue", extra="panel documentation-note"),
                children=[
                    html.Div(className="card-header panel-header", children=[html.H2("Continue exploring")]),
                    html.Div(className="card-body documentation-note-body", children=[html.P("Use these definitions while configuring a Parameter Sweep or Particle Explorer run."), html.A("Back to documentation →", href="/documentation", className="inline-action")]),
                ],
            ),
        ],
    )


def _syntax_card():
    examples = (("600", "One scalar value"), ("600,800,1000", "An explicit list"), ("400:1400:8", "Eight evenly spaced values"), ("LP01,HG11", "A list of names or modes"))
    return html.Section(
        className=Card.classes(color="blue", extra="panel documentation-detail-card"),
        children=[
            html.Div(className="card-header panel-header", children=[html.H2("Field syntax")]),
            html.Div(className="card-body", children=[html.P("Most text fields accept compact batch input. The same notation works for optical quantities, material values, angles, and named modes."), html.Div([html.Div(className="documentation-syntax-row", children=[html.Code(value), html.Span(description)]) for value, description in examples], className="documentation-syntax-list"), html.P("Keep the X axis on a field that actually varies if you want a clean one-dimensional plot.", className="documentation-callout")]),
        ],
    )


def _vocabulary_card():
    rows = (("Source", "The incident illumination, such as Gaussian or plane wave."), ("Scatterer", "The object being simulated, such as a sphere or core-shell particle."), ("Detector", "The collection model used for detector-specific measures and coupling."), ("Measure", "The quantity computed from the selected source, scatterer, and detector."), ("Representation", "The mathematical view used to display a result, such as S1/S2, Stokes, or far-field intensity."), ("Sweep", "A calculation over combinations of values supplied in fields with lists or ranges."))
    return html.Section(
        className=Card.classes(color="purple", extra="panel documentation-detail-card"),
        children=[html.Div(className="card-header panel-header", children=[html.H2("Core vocabulary")]), html.Div(className="card-body documentation-definition-list", children=[html.Div([html.Strong(term), html.Span(description)]) for term, description in rows])],
    )


def _detector_definitions_card():
    definitions = (("Photodiode", "Integrates collected power over the detector geometry and supports detector-specific measures."), ("Coherent mode", "Projects the collected field onto a selected spatial mode, such as LP01 or HG11, preserving phase information."), ("No detector", "Runs source/scatterer calculations without a detector. Detector coupling measures are unavailable in this mode."))
    return html.Section(
        className=Card.classes(color="orange", extra="panel documentation-detail-card"),
        children=[html.Div(className="card-header panel-header", children=[html.H2("Detector definitions")]), html.Div(className="card-body documentation-definition-list", children=[html.Div([html.Strong(name), html.Span(description)]) for name, description in definitions])],
    )


def _model_group(title: str, *models: str):
    return html.Div(className="documentation-model-group", children=[html.H3(title), html.Div([html.Span(model, className="documentation-model-pill") for model in models], className="documentation-model-pills")])
