"""Token-gated administration dashboard for server-side usage counters."""

import hmac
import os
from collections import deque
from threading import Lock
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from dash import dcc, html
from flask import Response, has_request_context, redirect, request
from itsdangerous import BadData, URLSafeTimedSerializer

from PyMieSimX.gui import usage_metrics
from PyMieSimX.gui.components import Card
from PyMieSimX.gui.visit_location import request_location


ADMIN_TOKEN_ENV_VAR = "PYMIESIMX_ADMIN_TOKEN"
ADMIN_COOKIE = "pymiesimx-admin"
ADMIN_SESSION_SECONDS = 30 * 60
REFRESH_INTERVAL_MILLISECONDS = 30_000


_PUBLIC_PAGES = frozenset({
    "/", "/experiment", "/single", "/population", "/examples", "/documentation", "/settings",
})
_recent_visits: deque[tuple[str, str, str]] = deque(maxlen=200)
_recent_visits_lock = Lock()


def record_page_visit(*, route: str) -> None:
    """Keep a bounded history of public page visits for this process."""
    if route in _PUBLIC_PAGES:
        visited_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        location = request_location()
        with _recent_visits_lock:
            _recent_visits.appendleft((visited_at, route, location))
        usage_metrics.save_page_visit(route=route, location=location)


def build_recent_visits() -> html.Div:
    """Render the latest public page visits without collecting visitor identifiers."""
    shared_visits = usage_metrics.load_page_visits()
    with _recent_visits_lock:
        visits = tuple(_recent_visits if shared_visits is None else shared_visits)
    if not visits:
        return html.Div("No public page visits recorded.")
    return html.Div(
        html.Table([
            html.Thead(html.Tr([html.Th("Visited at"), html.Th("Page"), html.Th("Location")])),
            html.Tbody([
                html.Tr([
                    html.Td(visited_at),
                    html.Td(route),
                    html.Td(location or "Unavailable"),
                ])
                for visited_at, route, location in visits
            ]),
        ], className="admin-activity-table"),
        className="admin-activity-scroll",
    )


@dataclass(frozen=True)
class AdminDashboardData:
    """Snapshot displayed by the administration dashboard."""

    metrics: usage_metrics.UsageMetrics = field(default_factory=usage_metrics.UsageMetrics)
    generated_at: str = ""


def is_admin_access_granted(provided_token: Any) -> bool:
    """Return whether the provided token exactly matches server configuration."""
    configured_token = os.getenv(ADMIN_TOKEN_ENV_VAR, "").strip()
    candidate_token = str(provided_token or "").strip()
    return bool(configured_token and candidate_token and hmac.compare_digest(configured_token.encode(), candidate_token.encode()))


def _admin_serializer(*, token: str) -> URLSafeTimedSerializer:
    """Build the signer used by all workers for administrator sessions."""
    return URLSafeTimedSerializer(token, salt="pymiesimx-admin-session")


def has_admin_session() -> bool:
    """Verify the signed administrator cookie and its expiry on every request."""
    token = os.getenv(ADMIN_TOKEN_ENV_VAR, "").strip()
    if not token or not has_request_context():
        return False
    cookie = request.cookies.get(ADMIN_COOKIE)
    if not cookie:
        return False
    try:
        return (
            _admin_serializer(token=token).loads(cookie, max_age=ADMIN_SESSION_SECONDS)
            == "admin"
        )
    except BadData:
        return False


def admin_login() -> Response:
    """Exchange a submitted administrator credential for a short-lived cookie."""
    token = os.getenv(ADMIN_TOKEN_ENV_VAR, "").strip()
    error = ""
    status = 200
    if not token:
        error = "Administrator access is unavailable on this server."
        status = 404
    elif request.method == "POST":
        if is_admin_access_granted(request.form.get("token", "")):
            response = redirect("/admin", code=303)
            response.set_cookie(
                ADMIN_COOKIE,
                _admin_serializer(token=token).dumps("admin"),
                max_age=ADMIN_SESSION_SECONDS,
                secure=os.getenv("RENDER") == "true" or request.is_secure,
                httponly=True,
                samesite="Strict",
            )
            response.headers["Cache-Control"] = "no-store"
            return response
        error = "The administrator token was incorrect."
        status = 403

    form = ""
    if token:
        form = """
        <form method="post" action="/admin/login">
            <label for="token">Administrator token</label>
            <input id="token" name="token" type="password" autocomplete="current-password" required>
            <button type="submit">Sign in</button>
        </form>"""
    return Response(
        f"""<!doctype html>
        <html lang="en"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="/assets/admin-login.css">
        <title>Administrator sign-in · PyMieSimX</title></head>
        <body class="pymiesimx-admin-login"><main><h1>Administrator sign-in</h1>
        <p role="status">{error}</p>{form}
        <a href="/">Return to PyMieSimX</a></main></body></html>""",
        status=status,
        mimetype="text/html",
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )


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


def build_admin_page(token: str | None = None) -> html.Div:
    """Build the hidden dashboard or an intentionally generic denial page."""
    if not has_admin_session() and not is_admin_access_granted(token):
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
                className="admin-header",
                children=[
                    html.H1("Administration"),
                    html.P("Server-side PyMieSimX usage metrics.", className="admin-description"),
                    html.Div(
                        [
                            html.Span(values[3], id="admin-last-updated"),
                            html.Button("Refresh", id="admin-refresh-button", n_clicks=0, className="admin-refresh"),
                        ],
                        className="admin-toolbar",
                    ),
                ],
            ),
            html.Div(
                [
                    html.Section(
                        className="admin-metric-card",
                        children=[
                            html.Div(value, id=value_id, className="admin-metric-value"),
                            html.Div(label, className="admin-metric-label"),
                        ],
                    )
                    for value_id, value, label in tiles
                ],
                className="admin-metric-grid",
            ),
            html.Section([
                html.Header([
                    html.H2("Recent activity"),
                    html.P("Latest 200 public page visits. Without PostgreSQL, activity is limited to the current server process."),
                ]),
                html.Div(build_recent_visits(), id="admin-recent-visits"),
            ], className="admin-activity-card"),
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
