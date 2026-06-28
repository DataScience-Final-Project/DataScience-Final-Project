import json
import re
import pandas as pd
import geopandas as gpd
from pyrosm import OSM
from pathlib import Path

# =========================================================
# CONFIG (כמו אצלך)
# =========================================================
POI_TYPES = {
    "school": {"id": 1, "filter": {"amenity": ["school"]}, "importance": 0.6},
    "kindergarten": {"id": 2, "filter": {"amenity": ["kindergarten"]}, "importance": 0.4},

    "train_station": {"id": 3, "filter": {"railway": ["station", "halt"]}, "importance": 1.0},
    "light_rail_stop": {"id": 4, "filter": {"railway": ["tram_stop"]}, "importance": 0.8},
    "bus_stop": {"id": 5, "filter": {"highway": ["bus_stop"]}, "importance": 0.3},

    "health_all": {
        "id": 6,
        "filter": {
            "amenity": ["hospital", "clinic", "doctors"],
            "healthcare": ["hospital", "clinic", "doctor", "doctors"]
        },
        "importance": 0.9
    },

    "park": {"id": 8, "filter": {"leisure": ["park"]}, "importance": 0.3},
    "supermarket": {"id": 9, "filter": {"shop": ["supermarket"]}, "importance": 0.5},
    "mall": {"id": 10, "filter": {"shop": ["mall"]}, "importance": 0.7},

    "office_building": {"id": 11, "filter": {"building": ["office", "commercial"]}, "importance": 0.4},
    "commercial_landuse": {"id": 11, "filter": {"landuse": ["commercial", "industrial"]}, "importance": 0.4},

    "hotel": {"id": 12, "filter": {"tourism": ["hotel"]}, "importance": 0.4},
}

ISRAEL_BBOX_4326 = (34.2, 29.4, 35.9, 33.4)

# =========================================================
# UTILS (כמו אצלך)
# =========================================================
def _to_tags(x):
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            return {}
    return {}

def _clean_str(x):
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    s = str(x).strip()
    if not s or s.lower() == "none":
        return ""
    return s

def pick_names(row):
    tags = _to_tags(row.get("tags"))
    name = _clean_str(row.get("name")) or _clean_str(tags.get("name"))
    he = (_clean_str(row.get("name:he")) or _clean_str(tags.get("name:he")) or name)
    en = (_clean_str(row.get("name:en")) or _clean_str(tags.get("name:en")) or _clean_str(tags.get("int_name")) or name)
    return he.strip(), en.strip(), tags

def parse_int(x):
    if x is None:
        return None
    s = str(x).strip()
    m = re.search(r"\d+", s.replace(",", ""))
    return int(m.group()) if m else None

def normalize_geom_to_point(geom):
    if geom is None:
        return None
    gt = getattr(geom, "geom_type", None)
    if gt in ("Polygon", "MultiPolygon"):
        return geom.representative_point()
    return geom

def keep_tags(tags: dict, poi_type: str):
    if not isinstance(tags, dict):
        return {}
    common = ["operator", "network", "brand", "brand:wikidata"]
    transport = ["station", "railway", "public_transport", "route_ref"]
    health = ["amenity", "healthcare", "emergency", "beds", "operator", "brand", "brand:wikidata"]
    edu = ["isced:level", "school:level"]

    keep = set(common)
    if poi_type in ("train_station", "light_rail_stop", "bus_stop"):
        keep |= set(transport)
    if poi_type in ("hospital_major", "hospital_general", "hospital_specialized", "clinic"):
        keep |= set(health)
    if poi_type in ("school", "kindergarten"):
        keep |= set(edu)

    out = {}
    for k in keep:
        v = tags.get(k)
        if v is not None and str(v).strip() and str(v).strip().lower() != "none":
            out[k] = v
    return out

# =========================================================
# ISRAEL BOUNDARY (כמו אצלך)
# =========================================================
def _iso_like(tags: dict) -> bool:
    if not isinstance(tags, dict):
        return False
    vals = []
    for k in ["ISO3166-1", "ISO3166-1:alpha2", "is_in:country_code", "addr:country",
              "country_code", "country", "short_name", "name", "int_name"]:
        v = tags.get(k)
        if v:
            vals.append(str(v).strip())
    big = " | ".join(vals).lower()
    return (" il " in f" {big} ") or ("israel" in big) or ("ישראל" in big)

def _boundary_best_polygon_2039(bdf_4326: gpd.GeoDataFrame):
    b = gpd.GeoDataFrame(bdf_4326, geometry="geometry", crs="EPSG:4326").copy()
    b_m = b.to_crs(epsg=2039)
    b_m["area_m2"] = b_m.geometry.area
    return b_m.sort_values("area_m2", ascending=False).iloc[0].geometry

def build_israel_geom_2039(osm_obj: OSM):
    name_candidates = ["ישראל", "Israel", "State of Israel", "إسرائيل", "دولة إسرائيل"]
    for nm in name_candidates:
        try:
            b = osm_obj.get_boundaries(boundary_type="administrative", name=nm)
            if b is not None and len(b) > 0:
                return _boundary_best_polygon_2039(b), f"osm.get_boundaries(name='{nm}')"
        except Exception:
            pass

    try:
        b = osm_obj.get_boundaries(boundary_type="administrative")
        if b is not None and len(b) > 0:
            b = gpd.GeoDataFrame(b, geometry="geometry", crs="EPSG:4326").copy()
            if "tags" in b.columns:
                b["tags_d"] = b["tags"].apply(_to_tags)
                cand = b[b["tags_d"].apply(_iso_like)].copy()
                if len(cand) > 0:
                    return _boundary_best_polygon_2039(cand), "osm.get_boundaries(all)+filter"
    except Exception:
        pass

    raise RuntimeError("Could not build Israel boundary from PBF via pyrosm.get_boundaries().")

def filter_israel(gdf_4326: gpd.GeoDataFrame, israel_geom_2039):
    if gdf_4326 is None or len(gdf_4326) == 0:
        return gdf_4326
    gdf = gpd.GeoDataFrame(gdf_4326, geometry="geometry", crs="EPSG:4326").copy()
    gdf = gdf.cx[ISRAEL_BBOX_4326[0]:ISRAEL_BBOX_4326[2], ISRAEL_BBOX_4326[1]:ISRAEL_BBOX_4326[3]].copy()
    if len(gdf) == 0:
        return gdf
    gdf_m = gdf.to_crs(epsg=2039)
    gdf_m = gdf_m[gdf_m.geometry.intersects(israel_geom_2039)].copy()
    return gdf_m.to_crs(epsg=4326)

# =========================================================
# HEALTH REGEX + classify + post_filter (כמו אצלך)
# =========================================================
HOSPITAL_WORDS = re.compile(r'(?:\bhospital\b|مستشفى|בית חולים|בי\"ח|בי׳׳ח|קריה רפואית)', re.I)
HOSPITAL_SOFT_HINTS = re.compile(r'(?:מרכז רפואי|medical center|medical centre|healthcare campus|medical campus)', re.I)

PHARM_LAB_WORDS = re.compile(
    r'(?:pharmacy|drugstore|super[- ]?pharm|covid|test|laboratory|lab|x[- ]?ray|imaging|radiology|'
    r'optic|optics|optomet|dental|dentist|orthodont|'
    r'physio|physiotherap|rehab clinic|'
    r'בית מרקחת|סופר ?פארם|קורונה|בדיקה|מעבדה|רנטגן|הדמיה|'
    r'אופטיק|אופטיקה|אופטומטר|שיניים|רופא שיניים|מרפאת שיניים|אורתודונט|'
    r'פיזיו|פיזיותרפ|'
    r'صيدلية|مختبر|تحليل|اشعة|تصوير|طب الاسنان)',
    re.I
)

BAD_WORDS = re.compile(
    r'(?:mosque|مسجد|church|كنيسة|synagogue|בית כנסת|'
    r'school|בית ספר|kindergarten|nursery|גן ילדים|'
    r'vet|veterin)',
    re.I
)

CLINIC_WORDS = re.compile(
    r'(?:clinic|health center|health centre|phc|primary care|polyclinic|urgent care|walk[- ]?in|family health|'
    r'physio|fizio|'
    r'מרפאה|קופת חולים|טיפת חלב|מרכז בריאות|פיזיותרפיה|פיזיו|מכון|مركز صحي|عيادة)',
    re.I
)

SPECIALIZED_WORDS = re.compile(
    r'(?:psychiatr|mental|rehab|rehabil|geriat|geriatr|nursing|long[- ]?term|'
    r'שיקום|שיקומי|גריאטר|גריאטרי|פסיכיאטר|בריאות הנפש|إعادة تأهيل|نفسي|طب نفسي)',
    re.I
)

BIG_HOSPITAL_HINTS = re.compile(
    r'(?:שיבא|תל השומר|איכילוב|רמב\"ם|סורוקה|הדסה|שערי צדק|וולפסון|קפלן|הלל יפה|ברזילי|מאיר|בילינסון|אסף הרופא|זיו|לגליל|העמק|פוריה|לניאדו|בני ציון)',
    re.I
)

HOSPITAL_BRANDS = re.compile(
    r'(?:assuta|אסותא|herzliya medical center|הרצליה מדיקל|elisha|אלישע|'
    r'shaarei zedek|שערי צדק|bikur cholim|ביקור חולים|mayanei hayeshua|מעייני הישועה)',
    re.I
)

COSMETIC_DENTAL_WORDS = re.compile(
    r'(?:smile|design|beauty|aesthetic|cosmetic|dental|dentist|orthodont|'
    r'סמייל|עיצוב|יופי|אסתטיקה|קוסמטיקה|שיניים|רופא שיניים|אורתודונט)',
    re.I
)

FORCE_CLINIC_HINTS = re.compile(r'(?:terem|טרם|עזרה למרפא|md?a|מד\"א|מגן דוד אדום)', re.I)

def classify_health_row(tags: dict, name_he: str, name_en: str, area_m2=None):
    a = str(tags.get("amenity", "")).lower()
    h = str(tags.get("healthcare", "")).lower()
    emergency = str(tags.get("emergency", "")).lower()
    beds = parse_int(tags.get("beds"))

    name = " ".join([name_en or "", name_he or ""]).strip()
    if not name:
        return None

    if BAD_WORDS.search(name):
        return None

    if PHARM_LAB_WORDS.search(name) or COSMETIC_DENTAL_WORDS.search(name) or FORCE_CLINIC_HINTS.search(name):
        return "clinic"

    if a in ("clinic", "doctors") or h in ("clinic", "doctor", "doctors"):
        return "clinic"

    if CLINIC_WORDS.search(name) and not HOSPITAL_WORDS.search(name) and a != "hospital" and h != "hospital":
        return "clinic"

    has_hospital_tag = (a == "hospital") or (h == "hospital")
    has_strict_hosp_name = bool(HOSPITAL_WORDS.search(name))
    has_brand = bool(HOSPITAL_BRANDS.search(name))
    has_big = bool(BIG_HOSPITAL_HINTS.search(name))

    is_hospitalish = has_hospital_tag or has_strict_hosp_name or has_brand or has_big
    if not is_hospitalish:
        return "clinic" if HOSPITAL_SOFT_HINTS.search(name) else None

    if SPECIALIZED_WORDS.search(name):
        return "hospital_specialized"

    major_signals = 0
    if emergency in ("yes", "true", "1"):
        major_signals += 1
    if beds is not None and beds >= 150:
        major_signals += 1
    if area_m2 is not None and area_m2 >= 50_000:
        major_signals += 1
    if has_big:
        major_signals += 1

    if major_signals >= 2:
        return "hospital_major"

    return "hospital_general"

HOSPITAL_BUILDING_NOISE2 = re.compile(
    r'(?:building|ward|department|campus|block|unit|wing|'
    r'בניין|מחלקה|אגף|יחידה|קומה|מבנה|'
    r'مبنى|قسم|جناح|وحدة)',
    re.I
)

def _full_name(row) -> str:
    return (" ".join([str(row.get("name_en") or ""), str(row.get("name_he") or "")])).strip()

def promote_clinic_to_hospital(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    nm = df.apply(_full_name, axis=1)

    is_clinic = df["poi_type"].eq("clinic")
    tags_d = df["tags_keep"].apply(_to_tags)
    a = tags_d.apply(lambda d: str(d.get("amenity", "")).lower())
    h = tags_d.apply(lambda d: str(d.get("healthcare", "")).lower())
    emergency = tags_d.apply(lambda d: str(d.get("emergency", "")).lower())

    excl = (
        nm.str.contains(PHARM_LAB_WORDS, na=False)
        | nm.str.contains(COSMETIC_DENTAL_WORDS, na=False)
        | nm.str.contains(FORCE_CLINIC_HINTS, na=False)
    )

    has_hosp_tag = a.eq("hospital") | h.eq("hospital")
    has_strict_name = nm.str.contains(HOSPITAL_WORDS, na=False)
    has_brand = nm.str.contains(HOSPITAL_BRANDS, na=False)
    has_big = nm.str.contains(BIG_HOSPITAL_HINTS, na=False)

    promote = is_clinic & ~excl & (has_hosp_tag | has_strict_name | has_brand | has_big)

    spec = promote & nm.str.contains(SPECIALIZED_WORDS, na=False)
    df.loc[spec, "poi_type"] = "hospital_specialized"
    df.loc[spec, "poi_type_id"] = 6
    df.loc[spec, "importance"] = 0.7

    gen = promote & ~spec
    df.loc[gen, "poi_type"] = "hospital_general"
    df.loc[gen, "poi_type_id"] = 6
    df.loc[gen, "importance"] = 0.9

    major = promote & (emergency.eq("yes") | has_big) & ~(h.isin(["clinic","doctor","doctors"]) | a.isin(["clinic","doctors"]))
    df.loc[major, "poi_type"] = "hospital_major"
    df.loc[major, "poi_type_id"] = 6
    df.loc[major, "importance"] = 1.0

    return df

def post_filter_health(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    nm = df.apply(_full_name, axis=1)

    df = df[nm.str.len() > 2].copy()
    nm = df.apply(_full_name, axis=1)

    df = df[~nm.str.contains(BAD_WORDS, na=False)].copy()
    nm = df.apply(_full_name, axis=1)

    mask_force_clinic = (
        nm.str.contains(COSMETIC_DENTAL_WORDS, na=False)
        | nm.str.contains(PHARM_LAB_WORDS, na=False)
        | nm.str.contains(FORCE_CLINIC_HINTS, na=False)
    )
    df.loc[mask_force_clinic, "poi_type"] = "clinic"
    df.loc[mask_force_clinic, "poi_type_id"] = 7
    df.loc[mask_force_clinic, "importance"] = 0.5
    nm = df.apply(_full_name, axis=1)

    keep_brand = (
        nm.str.contains(HOSPITAL_BRANDS, na=False)
        | nm.str.contains(BIG_HOSPITAL_HINTS, na=False)
        | nm.str.contains(HOSPITAL_WORDS, na=False)
        | (df["tags_keep"].apply(_to_tags).apply(lambda d: str(d.get("amenity", "")).lower()).eq("hospital"))
        | (df["tags_keep"].apply(_to_tags).apply(lambda d: str(d.get("healthcare", "")).lower()).eq("hospital"))
    )
    drop_noise = nm.str.contains(HOSPITAL_BUILDING_NOISE2, na=False)
    df = df[~(drop_noise & ~keep_brand)].copy()

    df = promote_clinic_to_hospital(df)

    nm = df.apply(_full_name, axis=1)
    mask = (
        nm.str.contains(FORCE_CLINIC_HINTS, na=False)
        | nm.str.contains(COSMETIC_DENTAL_WORDS, na=False)
        | nm.str.contains(PHARM_LAB_WORDS, na=False)
    )
    df.loc[mask, "poi_type"] = "clinic"
    df.loc[mask, "poi_type_id"] = 7
    df.loc[mask, "importance"] = 0.5

    return df

# THE MAIN EXTRACT FUNCTION
def extract_pois_gdf(
    file_path: str,
    do_post_filter_health: bool = True,
    return_debug_tags: bool = False,
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """
    מחזיר GeoDataFrame (EPSG:4326) של כל ה-POI.
    - אם do_post_filter_health=True: מפעיל post_filter_health (דורש tags_keep).
    - אם return_debug_tags=False: לא מחזיר tags_keep (כדי שיהיה נקי יותר להמשך DB).
    """
    osm = OSM(file_path)

    israel_geom_2039, boundary_src = build_israel_geom_2039(osm)
    if verbose:
        print(f"✅ Israel boundary ready (EPSG:2039) | source: {boundary_src}")

    all_rows = []

    for poi_name, cfg in POI_TYPES.items():
        gdf = osm.get_pois(custom_filter=cfg["filter"])
        if gdf is None or len(gdf) == 0:
            if verbose:
                print(poi_name, 0)
            continue

        gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
        gdf = filter_israel(gdf, israel_geom_2039)

        if len(gdf) == 0:
            if verbose:
                print(poi_name, 0)
            continue

        # area_m2 (לבריאות)
        gdf_m = gdf.to_crs(epsg=2039)
        gdf_m["area_m2"] = None
        poly_mask = gdf_m.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
        gdf_m.loc[poly_mask, "area_m2"] = gdf_m.loc[poly_mask].geometry.area
        gdf = gdf_m.to_crs(epsg=4326)

        if poi_name == "health_all":
            for _, r in gdf.iterrows():
                name_he, name_en, tags = pick_names(r)
                cls = classify_health_row(tags, name_he, name_en, r.get("area_m2"))
                if cls is None:
                    continue

                if cls == "clinic":
                    final_type, final_id, final_importance = "clinic", 7, 0.5
                elif cls == "hospital_major":
                    final_type, final_id, final_importance = "hospital_major", 6, 1.0
                elif cls == "hospital_specialized":
                    final_type, final_id, final_importance = "hospital_specialized", 6, 0.7
                else:
                    final_type, final_id, final_importance = "hospital_general", 6, 0.9

                osm_id = r.get("id")
                osm_type = r.get("osm_type")
                if pd.isna(osm_id):
                    continue

                geom = normalize_geom_to_point(r.geometry)

                row = {
                    "osm_id": int(osm_id),
                    "osm_type": _clean_str(osm_type),
                    "poi_type": final_type,
                    "poi_type_id": int(final_id),
                    "importance": float(final_importance),
                    "name_he": name_he,
                    "name_en": name_en,
                    "geometry": geom,
                    "source": "osm",
                    "tags_keep": json.dumps(keep_tags(tags, final_type), ensure_ascii=False),
                }
                all_rows.append(row)

            if verbose:
                print(poi_name, len(gdf))
            continue

        for _, r in gdf.iterrows():
            name_he, name_en, tags = pick_names(r)
            osm_id = r.get("id")
            osm_type = r.get("osm_type")
            if pd.isna(osm_id):
                continue

            geom = normalize_geom_to_point(r.geometry)

            row = {
                "osm_id": int(osm_id),
                "osm_type": _clean_str(osm_type),
                "poi_type": poi_name,
                "poi_type_id": int(cfg["id"]),
                "importance": float(cfg.get("importance", 0)),
                "name_he": name_he,
                "name_en": name_en,
                "geometry": geom,
                "source": "osm",
                "tags_keep": json.dumps(keep_tags(tags, poi_name), ensure_ascii=False),
            }
            all_rows.append(row)

        if verbose:
            print(poi_name, len(gdf))

    poi_db = gpd.GeoDataFrame(all_rows, geometry="geometry", crs="EPSG:4326")
    poi_db = poi_db.drop_duplicates(subset=["osm_id", "osm_type", "poi_type"]).reset_index(drop=True)

    if verbose:
        print("\n✅ DB-ready rows:", len(poi_db))
        print("\nCounts:")
        print(poi_db["poi_type"].value_counts())

    # ✅ חשוב: post_filter_health משנה רק את הבריאות.
    if do_post_filter_health:
        health_mask = poi_db["poi_type"].isin(["hospital_major", "hospital_general", "hospital_specialized", "clinic"])
        health_df = poi_db[health_mask].copy()
        health_df = post_filter_health(health_df)

        non_health = poi_db[~health_mask].copy()
        poi_db = pd.concat([non_health, health_df], ignore_index=True)
        poi_db = gpd.GeoDataFrame(poi_db, geometry="geometry", crs="EPSG:4326")

        if verbose:
            print("\n✅ After post-filter health counts:")
            print(poi_db[poi_db["poi_type"].isin(["hospital_major","hospital_general","hospital_specialized","clinic"])]["poi_type"].value_counts())

    # אם לא רוצים tags_keep החוצה (אבל השארנו פנימי בשביל ה-post_filter)
    if not return_debug_tags:
        poi_db = poi_db.drop(columns=["tags_keep"], errors="ignore")

    return poi_db
