"""Token-gated administration dashboard for server-side usage counters."""

import hmac
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from dash import dcc, html

from PyMieSimX.gui import usage_metrics
from PyMieSimX.gui.components import Card


ADMIN_TOKEN_ENV_VAR = "PYMIESIMX_ADMIN_TOKEN"
REFRESH_INTERVAL_MILLISECONDS = 30_000


@dataclass(frozen=True)
class AdminDashboardData:
    """Snapshot displayed by the administration dashboard."""

    metrics: usage_metrics.UsageMetrics = field(default_factory=usage_metrics.UsageMetrics)
    generated_at: str = ""


def is_admin_access_granted(provided_token: Any) -> bool:
    """Return whether the provided token exactly matches server configuration."""
    configured_token = os.getenv(ADMIN_TOKEN_ENV_VAR, "").strip()
    candidate_token = str(provided_token or "").strip()
    return bool(configured_token and candidate_token and hmac.compare_digest(configured_token, candidate_token))


def collect_admin_dashboard_data() -> AdminDashboardData:
    """Load the current server-side usage counters."""
    return AdminDashboardData(
        metrics=usage_metrics.load_usage_metrics(),
        generated_at=f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
    )


def metric_text(value: object) -> str:
    """Format a metric for display, including unavailable local values."""
    if isinstance(value, float) and value != value:
        return "NaN"
    return str(value)


def dashboard_values(data: AdminDashboardData) -> tuple[str, str, str, str]:
    """Return callback-ready metric values and update timestamp."""
    metrics = data.metrics
    return (
        metric_text(metrics.home_page_visit_count),
        metric_text(metrics.experiment_run_count),
        metric_text(metrics.single_run_count),
        f"Last updated: {data.generated_at}",
    )


def build_admin_page(token: str | None) -> html.Div:
    """Build the hidden dashboard or an intentionally generic denial page."""
    if not is_admin_access_granted(token):
        return html.Div(
            html.Section(
                className=Card.classes(color="blue", extra="admin-access-card"),
                children=[
                    html.H2("Page not available"),
                    html.P("The requested page is not available on this server."),
                ],
            ),
            className="page-content-stack admin-page",
        )

    values = dashboard_values(collect_admin_dashboard_data())
    tiles = (
        ("admin-home-page-visits", values[0], "Home page visits"),
        ("admin-experiment-runs", values[1], "Parameter sweeps"),
        ("admin-single-runs", values[2], "Particle explorations"),
    )
    return html.Div(
        className="page-content-stack admin-page",
        children=[
            dcc.Interval(id="admin-refresh-interval", interval=REFRESH_INTERVAL_MILLISECONDS, n_intervals=0),
            html.Section(
                className="page-hero",
                children=[
                    html.H1("Administration"),
                    html.P("Server-side PyMieSimX usage metrics.", className="hero-text"),
                    html.Div(
                        [
                            html.Span(values[3], id="admin-last-updated"),
                            html.Button("Refresh", id="admin-refresh-button", n_clicks=0, className="run-button"),
                        ],
                        className="admin-toolbar",
                    ),
                ],
            ),
            html.Div(
                [
                    html.Section(
                        className=Card.classes(color="blue", extra="admin-metric-card"),
                        children=[
                            html.Div(value, id=value_id, className="admin-metric-value"),
                            html.Div(label, className="admin-metric-label"),
                        ],
                    )
                    for value_id, value, label in tiles
                ],
                className="admin-metric-grid",
            ),
        ],
    )


__all__ = [
    "ADMIN_TOKEN_ENV_VAR",
    "AdminDashboardData",
    "build_admin_page",
    "collect_admin_dashboard_data",
    "dashboard_values",
    "is_admin_access_granted",
]
