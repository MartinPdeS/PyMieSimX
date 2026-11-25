"""Resolve approximate visit locations using IPinfo."""

import json
import os
from functools import lru_cache
from http.client import HTTPException
from ipaddress import ip_address
from urllib.request import Request, urlopen
from flask import has_request_context, request


@lru_cache(maxsize=1024)
def _lookup_location(*, address: str) -> str:
    """Fetch and cache the city, region and country for a public IP address.

    Parameters
    ----------
    address : str
        Validated IPv4 or IPv6 address.

    Returns
    -------
    str
        Available location fields, or "Unavailable" for an unmatched address.
    """
    headers = {"Accept": "application/json"}
    token = os.getenv("PYMIESIMX_IPINFO_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    lookup = Request(f"https://ipinfo.io/{address}/json", headers=headers)
    with urlopen(lookup, timeout=2) as response:
        record = json.load(response)
    if not isinstance(record, dict):
        return "Unavailable"
    parts = [record.get(key) for key in ("city", "region", "country")]
    return ", ".join(part.strip() for part in parts if isinstance(part, str) and part.strip()) or "Unavailable"


def request_location() -> str:
    """Return the available city, region and country for the current request."""
    if not has_request_context():
        return "Unavailable"
    try:
        proxy_count = int(os.getenv("PYMIESIMX_TRUSTED_PROXY_COUNT", "1" if os.getenv("RENDER") == "true" else "0"))
        address = request.remote_addr
        if proxy_count > 0:
            if "X-Forwarded-For" not in request.headers or len(request.access_route) < proxy_count:
                return "Unavailable"
            address = request.access_route[-proxy_count]
        parsed = ip_address(address or "")
        if not parsed.is_global or parsed.is_multicast or "%" in str(parsed):
            return "Unavailable"
        return _lookup_location(address=str(parsed))
    except (OSError, HTTPException, ValueError):
        return "Unavailable"
