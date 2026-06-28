import requests
import re
from math import hypot
from typing import Optional, Tuple, List
from poi.overrides import lookup_override

#CONFIGURATION
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "POI-Enrichment-Tool/6.0"}
KM_PER_DEGREE = 111.0  # Approx conversion for distance calculation
MAX_DIST_KM = 2.0  # Maximum allowed distance deviation

#HELPER FUNCTIONS
def clean_name_smart(name: str) -> str:
    """
    Prioritizes specific keywords (Savidor, Azrieli) to improve search recall.
    Falls back to removing generic stop words.
    """
    if not name:
        return ""

    name_lower = name.lower()

    # Priority keywords that solve specific edge cases
    priority_keywords = ["savidor", "azrieli", "technion", "sarona", "dizengoff"]
    for kw in priority_keywords:
        if kw in name_lower:
            return kw.capitalize() if kw.isascii() else kw

    # Standard cleaning: remove generic suffixes
    stop_words = ["center", "central", "railway", "station", "mall", "shopping", "kanyon", "hospital", "medical"]
    # Regex keeps alphanumeric characters and Hebrew letters
    tokens = re.sub(r"[^\w\s\u0590-\u05FF\"]", "", name).split()
    clean_tokens = [t for t in tokens if t.lower() not in stop_words]

    return " ".join(clean_tokens) if clean_tokens else name


def extract_year(sparql_result: dict) -> Optional[int]:
    """Extracts the year from a SPARQL date result (ISO format)."""
    if "openingDate" not in sparql_result:
        return None
    val = sparql_result["openingDate"]["value"]
    match = re.search(r"(\d{4})", val)
    return int(match.group(1)) if match else None


#WIKIDATA INTERACTION
def search_entities(search_term: str) -> List[str]:
    """
    Performs a Full-Text Search on Wikidata (action=query, list=search).
    Returns a list of QIDs (e.g., ['Q123', 'Q456']).
    """
    if not search_term:
        return []

    params = {
        "action": "query",
        "list": "search",
        "srsearch": search_term.replace('"', ''),
        "srlimit": 10,
        "format": "json"
    }

    try:
        r = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=10)
        data = r.json()
        # 'title' in list=search results is the QID
        return [item["title"] for item in data.get("query", {}).get("search", [])]
    except Exception:
        return []


def get_entity_details(qids: List[str]) -> List[dict]:
    """
    Fetches coordinates and opening dates for a list of QIDs via SPARQL.
    """
    if not qids:
        return []

    # Filter for valid QIDs only
    valid_qids = [q for q in qids if re.match(r'^Q\d+$', q)]
    if not valid_qids:
        return []

    values_clause = " ".join([f"wd:{qid}" for qid in valid_qids])

    query = f"""
    SELECT ?item ?openingDate ?lat ?lon WHERE {{
      VALUES ?item {{ {values_clause} }}

      # Try various date properties: Official opening, Inception, Start time
      OPTIONAL {{ ?item p:P1619/ps:P1619 ?openingDate . }}
      OPTIONAL {{ ?item p:P571/ps:P571 ?openingDate . }}
      OPTIONAL {{ ?item p:P580/ps:P580 ?openingDate . }}

      OPTIONAL {{
        ?item wdt:P625 ?coord .
        BIND(geof:latitude(?coord) AS ?lat)
        BIND(geof:longitude(?coord) AS ?lon)
      }}
    }}
    """

    try:
        r = requests.post(
            WIKIDATA_SPARQL,
            data={"query": query, "format": "json"},
            headers=HEADERS,
            timeout=15
        )
        if r.status_code == 200:
            return r.json()["results"]["bindings"]
    except Exception:
        pass
    return []

# MAIN GET DATE FUNCTION
def enrich_poi(name_en: str, name_he: str, poi_type: str, lat: float, lon: float) -> Optional[int]:
    """
    Main orchestration function.
    Returns: (Year, Wikidata_ID) or (None, None) if not found.
    """

    #first try to find poi in overrides file
    year = lookup_override(name_en, name_he, poi_type)
    if year:
        return year

    candidate_qids = set()

    # Strategy 1: Search Original Hebrew Name (High Precision in Full Text)
    if name_he:
        candidate_qids.update(search_entities(name_he))

    # Strategy 2: Search Original English Name
    if name_en:
        candidate_qids.update(search_entities(name_en))

    # Strategy 3: Search "Smart" Name (Keyword extraction)
    smart_name = clean_name_smart(name_en)
    if smart_name and smart_name != name_en:
        candidate_qids.update(search_entities(smart_name))

    if not candidate_qids:
        return None

    # Fetch details for all candidates
    details = get_entity_details(list(candidate_qids))
    valid_candidates = []

    for r in details:
        qid = r["item"]["value"].split("/")[-1]
        year = extract_year(r)

        # Calculate Distance
        dist = 9999.0
        if "lat" in r and "lon" in r:
            try:
                d_lat = float(r["lat"]["value"]) - lat
                d_lon = float(r["lon"]["value"]) - lon
                dist = hypot(d_lat, d_lon) * KM_PER_DEGREE
            except (ValueError, TypeError):
                pass

        # Validate by Distance
        if dist <= MAX_DIST_KM:
            valid_candidates.append({
                "qid": qid,
                "year": year,
                "dist": dist,
                "has_date": year is not None
            })

    if not valid_candidates:
        return None

    # Sort: 1. Has Date (True first), 2. Closest Distance
    valid_candidates.sort(key=lambda x: (not x["has_date"], x["dist"]))
    best = valid_candidates[0]

    return best["year"]