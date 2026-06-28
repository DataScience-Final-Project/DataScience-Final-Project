import uuid
import geopandas as gpd
from osm_handler import extract_pois_gdf
from enrichment import enrich_poi
from shapely.geometry import Point
from pathlib import Path
from etl.common.paths import OSM_PBF, PROCESSED_DIR

def geom_to_point(geom):
    if geom is None:
        return None
    gt = getattr(geom, "geom_type", None)
    if gt == "Point":
        return geom
    if gt in ("Polygon", "MultiPolygon", "LineString", "MultiLineString"):
        return geom.representative_point()
    return geom

def main():
    gdf = extract_pois_gdf(str(OSM_PBF), do_post_filter_health=True, return_debug_tags=False, verbose=True)

    # ensure EPSG:4326
    gdf = gdf.to_crs("EPSG:4326")

    # ensure all Point geometries (fixes your error)
    gdf["geometry"] = gdf["geometry"].apply(geom_to_point)
    gdf = gdf[gdf["geometry"].notna()].copy()

    # opening_year (leave None if cannot enrich)
    def get_opening_year(r):
        print("getting the dates for the poi")
        name_en = (r.get("name_en") or "").strip()
        name_he = (r.get("name_he") or "").strip()

        # אם אין שם בכלל, enrichment כנראה לא יעזור -> נשאיר None
        if not name_en and not name_he:
            return None

        return enrich_poi(
            poi_type=r["poi_type"],
            name_en=name_en,
            name_he=name_he,
            lat=float(r.geometry.y),
            lon=float(r.geometry.x),
        )

    gdf["opening_year"] = gdf.apply(get_opening_year, axis=1)

    # poi_id UUID
    gdf["poi_id"] = [str(uuid.uuid4()) for _ in range(len(gdf))]

    # saving location as geom for postGis
    gdf["geom_wkt"] = gdf.geometry.apply(lambda p: p.wkt)

    db_df = gdf[["poi_id", "name_en", "name_he", "opening_year", "geom_wkt", "poi_type_id"]].rename(
        columns={"poi_type_id": "poi_type"}
    )

    out_path = Path(PROCESSED_DIR) / "pois_for_db.csv"
    db_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print("✅ Saved pois_for_db.csv", len(db_df))
    print("✅ opening_year nulls:", db_df["opening_year"].isna().sum())

if __name__ == "__main__":
    main()
