import json
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
OVERRIDES_FILE = BASE_DIR / "overrides.json"

def lookup_override(name_en: str, name_he: str, poi_type: str) -> Optional[int]:
    """
    Checks the local JSON file for a manually defined year.
    Tries looking up by English name first, then Hebrew name.
    """
    if not OVERRIDES_FILE.exists():
        return None

    try:
        with open(OVERRIDES_FILE, "r", encoding="utf-8") as f:
            overrides = json.load(f)

        # Try Key 1: English Name (e.g., "mall::Azrieli Mall")
        if name_en:
            key_en = f"{poi_type}::{name_en}"
            if key_en in overrides:
                return overrides[key_en]

        # Try Key 2: Hebrew Name (e.g., "mall::קניון עזריאלי")
        if name_he:
            key_he = f"{poi_type}::{name_he}"
            if key_he in overrides:
                return overrides[key_he]

    except Exception as e:
        print(f"Warning: Could not read overrides file: {e}")

    return None