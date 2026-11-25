"""Resolve approximate visit locations from a local GeoIP City database."""

import os
from ipaddress import ip_address
from flask import has_request_context, request


def request_location() -> str:
    """Return the available city, region and country for the current request."""
    database_path = os.getenv("PYMIESIMX_GEOIP_DATABASE", "").strip()
    if not database_path or not has_request_context():
        return "Unavailable"
    try:
        proxy_count = int(os.getenv("PYMIESIMX_TRUSTED_PROXY_COUNT", "1" if os.getenv("RENDER") == "true" else "0"))
        address = request.remote_addr
        if proxy_count > 0:
            if "X-Forwarded-For" not in request.headers or len(request.access_route) < proxy_count:
                return "Unavailable"
            address = request.access_route[-proxy_count]
        parsed = ip_address(address or "")
        if not parsed.is_global or parsed.is_multicast:
            return "Unavailable"
        # Local installations can run without the optional GeoIP reader.
        import maxminddb

        with maxminddb.open_database(database_path) as database:
            record = database.get(str(parsed)) or {}
        subdivisions = record.get("subdivisions") or [{}]
        parts = (
            record.get("city", {}).get("names", {}).get("en"),
            subdivisions[-1].get("names", {}).get("en"),
            record.get("country", {}).get("iso_code"),
        )
        return ", ".join(part for part in parts if part) or "Unavailable"
    except (ImportError, OSError, ValueError, RuntimeError):
        return "Unavailable"
