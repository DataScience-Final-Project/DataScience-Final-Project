import psycopg
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.cluster import DBSCAN
from shapely.geometry import MultiPoint
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy.stats import spearmanr
import xgboost as xgb

CUTOFF = 2018
VAL_TIME = 2

conn = psycopg.connect(
    host="10.10.248.102",
    port=5432,
    dbname="trendsense",
    user="postgres",
    password="Aa123456",
)

# Removed health_score_now and health_score_future
QUERY = """
SELECT snap.property_id, prop.lon, prop.lat, snap.snapshot_year, horizon_years, snap.city_name, 
       snap.location_accuracy, snap.num_rooms, snap.building_year, snap.building_floors, snap.property_type, 
       price_t0, price_t1, pct_change, log_change, school_score_now, train_score_now, 
       park_score_now, supermarket_score_now, mall_score_now, hotel_score_now, 
       school_score_future, train_score_future,  park_score_future, 
       supermarket_score_future, mall_score_future, hotel_score_future, kindergarten_score_now, 
       light_rail_score_now, bus_score_now, hospital_score_now, clinic_score_now, kindergarten_score_future, 
       light_rail_score_future, bus_score_future, hospital_score_future, clinic_score_future
FROM public.property_features_snapshot as snap
JOIN public.properties as prop ON prop.property_id = snap.property_id;
"""


df = pd.read_sql_query(QUERY, conn)
conn.close()


# =============================================================================
# IMPLEMENTATION OF THE ALGORITHM
# =============================================================================
#
# Notes on the columns:
#   *_score_now    -> environment score (0..1) at snapshot_year
#   *_score_future -> environment score (0..1) at snapshot_year + horizon_years
#   price_t0       -> price at snapshot_year
#   price_t1       -> price at snapshot_year + horizon_years
#   log_change     -> ln(price_t1 / price_t0)   (our regression target)
# =============================================================================

# ----------------------- configuration -----------------------
TARGET = "log_change"          # raw log return (what the map ultimately shows)
REL_TARGET = "y_rel"           # cohort-relative target the MODEL actually learns
EMBARGO_YEARS = VAL_TIME       # gap between train and test to limit time leakage
VAL_FRAC = 0.2                 # share of (latest) train years used for early stopping
DBSCAN_EPS_KM = 0.75           # neighbourhood radius in km
DBSCAN_MIN_SAMPLES = 8         # min properties to form a hotspot
EARTH_RADIUS_KM = 6371.0

POI_KEYS = [
    "school", "train", "park", "supermarket", "mall", "hotel",
    "kindergarten", "light_rail", "bus", "hospital", "clinic",
]
NOW_SCORES = [f"{k}_score_now" for k in POI_KEYS]
FUTURE_SCORES = [f"{k}_score_future" for k in POI_KEYS]


# ----------------------- feature engineering -----------------------
def engineer_features(data: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    d = data.copy()
    d["property_age"] = d["snapshot_year"] - d["building_year"]
    d["log_price_t0"] = np.log1p(d["price_t0"].clip(lower=0))

    delta_cols = []
    for k in POI_KEYS:
        col = f"{k}_score_delta"
        d[col] = d[f"{k}_score_future"] - d[f"{k}_score_now"]
        delta_cols.append(col)

    # --- aggregate accessibility scores ---
    d["now_score_mean"] = d[NOW_SCORES].mean(axis=1)
    d["future_score_mean"] = d[FUTURE_SCORES].mean(axis=1)
    d["delta_score_mean"] = d[delta_cols].mean(axis=1)

    # --- city as a numeric category (geography matters for RE growth) ---
    d["city_name"] = d["city_name"].fillna("UNK")
    d["city_code"] = LabelEncoder().fit_transform(d["city_name"].astype(str))

    feature_cols = (
        [
            "lon", "lat",
            "location_accuracy", "city_code",
            "num_rooms", "building_year", "building_floors", "property_type",
            "property_age", "log_price_t0",
            "now_score_mean", "future_score_mean", "delta_score_mean",
        ]
        + NOW_SCORES
        + FUTURE_SCORES
        + delta_cols
    )

    for col in feature_cols:
        d[col] = pd.to_numeric(d[col], errors="coerce")

    return d, feature_cols

def temporal_split(d: pd.DataFrame):
    train = d[d["snapshot_year"] < (CUTOFF - EMBARGO_YEARS)]
    test = d[d["snapshot_year"] >= CUTOFF]

    if len(train) == 0 or len(test) == 0:
        years = sorted(d["snapshot_year"].unique())
        split_idx = max(1, int(len(years) * 0.8))
        train_years = set(years[: max(1, split_idx - EMBARGO_YEARS)])
        test_years = set(years[split_idx:])
        train = d[d["snapshot_year"].isin(train_years)]
        test = d[d["snapshot_year"].isin(test_years)]

    return train, test

def report_metrics(label: str, y_true: np.ndarray, y_pred: np.ndarray) -> None:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred) if len(np.unique(y_true)) > 1 else float("nan")
    print(f"    {label:5} | n={len(y_true):>6} | MAE={mae:.4f} | RMSE={rmse:.4f} | R2={r2:.4f}")


def carve_validation(train: pd.DataFrame, frac: float = VAL_FRAC):
    """Hold out the LATEST train years for early stopping (temporal, not random)."""
    years = sorted(train["snapshot_year"].unique())
    if len(years) < 2:
        return train, train
    n_val = max(1, int(round(len(years) * frac)))
    val_years = set(years[-n_val:])
    core = train[~train["snapshot_year"].isin(val_years)]
    val = train[train["snapshot_year"].isin(val_years)]
    if len(core) == 0:  # safety for very short histories
        return train, train
    return core, val


def rank_ic(d: pd.DataFrame, y_col: str, pred_col: str) -> pd.Series:
    """Spearman rank correlation between prediction and outcome, per snapshot year.
    This is what really matters for ranking hotspots; adding a per-year constant
    (the cohort baseline) does not change the within-year ranking."""
    return d.groupby("snapshot_year").apply(
        lambda g: spearmanr(g[y_col], g[pred_col]).correlation if len(g) > 2 else np.nan
    )


df, FEATURES = engineer_features(df)

df = df[np.isfinite(df[TARGET]) & df["lat"].notna() & df["lon"].notna()].copy()

# --- relative target: remove the market-wide level per (horizon, year) ---
# Train and test years are disjoint, so this de-meaning does NOT leak between
# the two. The model learns spatial OUT-PERFORMANCE; the macro level is added
# back later so the map can still show raw "how much could I get" growth.
df["cohort_mean"] = df.groupby(["horizon_years", "snapshot_year"])[TARGET].transform("mean")
df[REL_TARGET] = df[TARGET] - df["cohort_mean"]

polygons = []
cluster_seq = 0

for horizon in sorted(df["horizon_years"].unique()):
    dh = df[df["horizon_years"] == horizon].copy()
    train_df, test_df = temporal_split(dh)

    if len(train_df) == 0 or len(test_df) == 0:
        print(f"\n=== Horizon {horizon}y: not enough data to split, skipping ===")
        continue

    core_df, val_df = carve_validation(train_df)

    X_train, y_train = core_df[FEATURES], core_df[REL_TARGET].values
    X_val, y_val = val_df[FEATURES], val_df[REL_TARGET].values
    X_test, y_test = test_df[FEATURES], test_df[REL_TARGET].values

    model = xgb.XGBRegressor(
        n_estimators=2000,
        learning_rate=0.02,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=20,
        reg_lambda=5.0,
        reg_alpha=1.0,
        objective="reg:pseudohubererror",   # robust to outliers -> better MAE/RMSE
        eval_metric="mae",
        early_stopping_rounds=50,
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    print(f"\n=== Horizon {horizon}y "
          f"(train years {int(train_df.snapshot_year.min())}-{int(train_df.snapshot_year.max())}, "
          f"test years {int(test_df.snapshot_year.min())}-{int(test_df.snapshot_year.max())}) ===")
    print(f"    best_iteration={model.best_iteration} / 2000  "
          f"(metrics below are on the COHORT-RELATIVE target)")
    report_metrics("TRAIN", y_train, model.predict(X_train))
    report_metrics("VAL",   y_val,   model.predict(X_val))
    report_metrics("TEST",  y_test,  model.predict(X_test))

    # ranking skill on the test set (per year) -- the real test for a hotspot map
    test_df = test_df.copy()
    test_df["pred_rel"] = model.predict(X_test)
    ic = rank_ic(test_df, REL_TARGET, "pred_rel")
    ic_txt = ", ".join(f"{int(y)}:{v:.3f}" for y, v in ic.dropna().items())
    print(f"    Rank IC (test): mean={ic.mean():.3f} | {ic_txt}")

    importances = (
        pd.Series(model.feature_importances_, index=FEATURES)
        .sort_values(ascending=False)
        .head(12)
    )
    print("    Top features:")
    for name, imp in importances.items():
        print(f"      {name:24} {imp:.4f}")

    # reconstruct RAW predicted growth for the map: relative prediction + the
    # market level of that period -> avg_growth stays a real "how much could I get"
    test_df["pred_log_change"] = test_df["pred_rel"] + test_df["cohort_mean"]
    test_df["pred_growth"] = np.exp(test_df["pred_log_change"] / horizon) - 1.0
    test_df["actual_growth"] = np.exp(test_df[TARGET] / horizon) - 1.0

    # --- RAW growth quality (annualised %, the actual numbers on the map) ---
    # NOTE: the market LEVEL is anchored to the period's cohort mean, so this
    # measures how well we place the *spatial* growth around that level.
    report_metrics(
        "RAW% prop",
        100 * test_df["actual_growth"].values,
        100 * test_df["pred_growth"].values,
    )

    latest = (
        test_df.sort_values("snapshot_year")
        .groupby("property_id", as_index=False)
        .last()
    )
    latest["actual_growth"] = np.exp(latest[TARGET] / horizon) - 1.0

    coords_rad = np.radians(latest[["lat", "lon"]].values)
    labels = DBSCAN(
        eps=DBSCAN_EPS_KM / EARTH_RADIUS_KM,
        min_samples=DBSCAN_MIN_SAMPLES,
        metric="haversine",
    ).fit_predict(coords_rad)
    latest["cluster"] = labels

    global_std = latest["pred_growth"].std() or 1e-9
    n_clusters = 0
    clu_pred, clu_actual = [], []   # for cluster-level (map) accuracy
    for cl in sorted(set(labels)):
        if cl == -1:
            continue
        members = latest[latest["cluster"] == cl]
        pts = MultiPoint(list(zip(members["lon"], members["lat"])))
        poly = pts.convex_hull
        if poly.geom_type != "Polygon":
            poly = poly.buffer(0.0005)   # ~50m, guarantees a valid polygon

        agreement = float(np.clip(1 - members["pred_growth"].std(skipna=True) / global_std, 0, 1))
        if np.isnan(agreement):
            agreement = 1.0
        support = min(1.0, len(members) / 20.0)
        certainty = round(0.6 * agreement + 0.4 * support, 4)

        clu_pred.append(float(members["pred_growth"].mean()))
        clu_actual.append(float(members["actual_growth"].mean()))

        polygons.append({
            "cluster_id": cluster_seq,
            "horizon_years": int(horizon),
            "avg_growth": round(float(members["pred_growth"].mean()), 6),
            "certainty": certainty,
            "wkt": poly.wkt,
        })
        cluster_seq += 1
        n_clusters += 1

    # --- accuracy of the polygons themselves (what the map shows) ---
    if len(clu_pred) > 1:
        report_metrics(
            "RAW% poly",
            100 * np.array(clu_actual),
            100 * np.array(clu_pred),
        )
    print(f"    -> {n_clusters} hotspot clusters from {len(latest)} properties")


# Save to DB
insert_query = """
        INSERT INTO public.growth_clusters (cluster_id, horizon_years, avg_growth, certainty, geom)
        VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326));
    """

data_to_insert = [
    (p['cluster_id'], p['horizon_years'], p['avg_growth'], p['certainty'], p['wkt'])
    for p in polygons
]

conn = psycopg.connect(
    host="10.10.248.102",
    port=5432,
    dbname="trendsense",
    user="postgres",
    password="Aa123456",
)
try:
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE public.growth_clusters;")
    print("\nstarting insertion")
    cur.executemany(insert_query, data_to_insert)
    conn.commit()
    print(f"Successfully saved {len(data_to_insert)} clusters to the database.") 
except Exception as e:
        print(f"Database error: {e}")

cur.close()
conn.close()
