"""Material catalog utilities backed by a bundled assets JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ASSET_CATALOG_PATH = Path(__file__).with_name("assets") / "materials-stock.json"

_FALLBACK_MATERIALS = [
    "fused_silica",
    "BK7",
    "water",
    "air",
    "polystyren",
    "soda_lime_glass",
    "crown",
    "flint",
    "BAK1",
    "BAF10",
]

_FALLBACK_SELLMEIER_REFERENCE = {
    "material": "fused_silica",
    "B1": "0.6961663",
    "B2": "0.4079426",
    "B3": "0.8974794",
    "C1_um2": "0.004679148",
    "C2_um2": "0.013512063",
    "C3_um2": "97.9340025",
}


def load_material_catalog() -> dict[str, Any]:
    """Load the material catalog JSON from assets with safe fallbacks."""
    try:
        with ASSET_CATALOG_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {
            "materials": list(_FALLBACK_MATERIALS),
            "sellmeier_reference": dict(_FALLBACK_SELLMEIER_REFERENCE),
        }

    materials = data.get("materials", _FALLBACK_MATERIALS)
    if not isinstance(materials, list):
        materials = list(_FALLBACK_MATERIALS)

    sellmeier_reference = data.get("sellmeier_reference", [_FALLBACK_SELLMEIER_REFERENCE])
    if isinstance(sellmeier_reference, dict):
        sellmeier_reference = [sellmeier_reference]
    if not isinstance(sellmeier_reference, list):
        sellmeier_reference = [dict(_FALLBACK_SELLMEIER_REFERENCE)]

    return {
        "materials": materials,
        "sellmeier_reference": sellmeier_reference,
    }


def material_dropdown_options() -> list[dict[str, str]]:
    """Build dropdown options from the JSON stock material catalog."""
    catalog = load_material_catalog()
    options = []

    for name in catalog["materials"]:
        if not isinstance(name, str):
            continue
        normalized = name.strip()
        if not normalized:
            continue

        options.append({"label": _to_display_name(normalized), "value": normalized})

    return options


def _to_display_name(name: str) -> str:
    """Convert canonical material keys into user-facing labels."""
    if "_" in name:
        return " ".join(part.upper() if part.isupper() else part.capitalize() for part in name.split("_"))
    if any(char.islower() for char in name) and any(char.isupper() for char in name):
        return name
    if name.isupper() or any(char.isdigit() for char in name):
        return name
    return name.capitalize()
