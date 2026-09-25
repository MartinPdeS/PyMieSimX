"""Material catalog utilities backed by a bundled assets JSON file."""


import json
from functools import lru_cache
import os
from pathlib import Path
from typing import Any

from PyMieSim.material import SellmeierMaterial, SellmeierMedium, TabulatedMaterial
from PyOptik import download_snapshot
from PyOptik.directories import user_data_path


ASSET_CATALOG_PATH = Path(__file__).with_name("assets") / "materials-stock.json"

_PYOPTIK_MATERIALS = (
    ("Fused silica", "Malitson", "main/SiO2/Malitson", "sellmeier"),
    ("BK7 optical glass", "SCHOTT P-BK7", "specs/SCHOTT-optical/P-BK7", "sellmeier"),
    ("Water", "Daimon, 19 °C", "main/H2O/Daimon-19.0C", "sellmeier"),
    ("Air", "Ciddor", "other/air/Ciddor", "sellmeier"),
    ("Polystyrene", "Sultanova", "organic/polystyrene/Sultanova", "sellmeier"),
    ("N-BAK1 optical glass", "SCHOTT", "specs/SCHOTT-optical/N-BAK1", "sellmeier"),
    ("N-BAF10 optical glass", "SCHOTT", "specs/SCHOTT-optical/N-BAF10", "sellmeier"),
    ("Silver", "Johnson & Christy", "main/Ag/Johnson", "tabulated"),
    ("Gold", "Olmon, evaporated", "main/Au/Olmon-ev", "tabulated"),
    ("Aluminium", "Rakić", "main/Al/Rakic", "tabulated"),
)

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
    "gold",
    "silver",
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


def ensure_material_catalog() -> Path:
    """Download PyOptik's full material snapshot when it is not installed."""
    configured_root = os.environ.get("PYMIESIM_PYOPTIK_DATA_ROOT")
    data_root = Path(configured_root).expanduser() if configured_root else user_data_path / "rii"
    catalog_file = data_root / "catalog-nk.yml"
    if not catalog_file.is_file():
        download_snapshot(data_root=data_root)
    material_dropdown_options.cache_clear()
    return catalog_file


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


@lru_cache(maxsize=2)
def material_dropdown_options(*, medium: bool = False) -> list[dict[str, str]]:
    """Build curated options from canonical, resolvable PyOptik pages."""
    options = []
    for name, source, identifier, model_kind in _PYOPTIK_MATERIALS:
        if medium and model_kind != "sellmeier":
            continue
        if not _material_is_available(identifier, medium=medium):
            continue
        options.append({"label": f"{name} · {source}", "value": identifier})
    return options


def _material_is_available(name: str, *, medium: bool) -> bool:
    """Return whether a named material resolves through the active catalog."""
    constructors = (SellmeierMedium,) if medium else (SellmeierMaterial, TabulatedMaterial)
    for constructor in constructors:
        try:
            constructor(name)
            return True
        except Exception:
            continue
    return False


def _to_display_name(name: str) -> str:
    """Convert canonical material keys into user-facing labels."""
    if "_" in name:
        return " ".join(part.upper() if part.isupper() else part.capitalize() for part in name.split("_"))
    if any(char.islower() for char in name) and any(char.isupper() for char in name):
        return name
    if name.isupper() or any(char.isdigit() for char in name):
        return name
    return name.capitalize()
