from pathlib import Path

def project_root() -> Path:
    # repo root = folder that contains python_service/
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "python_service").exists():
            return p
    raise RuntimeError("Repo root not found (expected python_service/ folder)")

ROOT = project_root()
PSVC = ROOT / "python_service"
DATA = PSVC / "data"

OSM_PBF = DATA / "raw" / "israel-and-palestine-251213.osm.pbf"
SALES_DIR = DATA / "raw" / "sales" / "cities_xlsx"
PROCESSED_DIR = DATA / "processed"
