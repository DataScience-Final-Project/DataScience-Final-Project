import psycopg
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.cluster import DBSCAN
from shapely.geometry import MultiPoint
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

# We pretend "today" is `cutoff`. Train uses rows whose realised horizon end
# (t1_year) finishes strictly before the validation window. Validation uses the
# most recent `val_time` years of realised data, and test is everything whose
# horizon ends in the future (after cutoff).
cutoff = 2018
val_time = 2

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

df['t1_year'] = df['snapshot_year'] + df['horizon_years']

# Two separate encoders — reusing one overwrote property_type_enc with the city
# encoding in the previous version.
le_type = LabelEncoder()
le_city = LabelEncoder()
df['property_type_enc'] = le_type.fit_transform(df['property_type'].astype(str))
df['city_name_enc']     = le_city.fit_transform(df['city_name'].astype(str))

# log(price_t0) is a much better feature than the raw price (mean reversion,
# scale invariance). log1p is safe for any non-negative price.
df['log_price_t0'] = np.log1p(df['price_t0'])

# --- National price index by snapshot_year (proxy for CPI / BoI housing index) ---
# We don't have an external macro series, so derive one from the data itself.
# For every snapshot_year present in the data (including future test snapshots
# whose snapshot_year <= cutoff) we compute the median log_price_t0 across all
# properties for that year. This leaks no future info — it's based on prices
# observed at the snapshot itself, not on realised growth. The result is a
# single national price-level number per year that the model can use to anchor
# its predictions in macro context.
national_index = (
    df.groupby('snapshot_year')['log_price_t0']
      .median()
      .rename('national_log_price_year')
      .reset_index()
)
df = df.merge(national_index, on='snapshot_year', how='left')

# --- Distance-to-anchor features ---
# Tree models can't combine raw lat & lon into "distance" via axis-aligned
# splits. Pre-computing haversine distance to the four major economic centres
# collapses that signal into single columns trees can split on cleanly.
ANCHORS = {
    'tlv':       (32.0853, 34.7818),  # Tel Aviv
    'jerusalem': (31.7683, 35.2137),
    'haifa':     (32.7940, 34.9896),
    'beersheba': (31.2518, 34.7913),
}

def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1r, lat2r = np.radians(lat1), np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))

distance_features = []
for name, (alat, alon) in ANCHORS.items():
    col = f'dist_to_{name}_km'
    df[col] = _haversine_km(df['lat'].values, df['lon'].values, alat, alon)
    distance_features.append(col)

# --- Property age at snapshot time ---
# Trees of depth 6 can derive this from (snapshot_year, building_year) but it
# costs them a split each time. Explicit is cheap and unambiguous.
df['property_age'] = df['snapshot_year'] - df['building_year']

# --- City-level momentum (expanding mean of past realised log_change) ---
# For each row with snapshot_year=S in city C, we look up the mean log_change
# of all sales in C with t1_year < S. Leak-free (those sales are observable
# at the snapshot moment) and acts as a stable "city quality" baseline.
# Empirically the expanding mean outperformed both a 5y rolling window and a
# dual long+recent variant in our multi-cutoff CV — the long-run mean is less
# noisy than short-window averages and trees already capture transient effects
# through other features (snapshot_year, national_log_price_year).
def _add_expanding_momentum(df, group_col, out_prefix):
    """Add {prefix}_growth (expanding mean) and {prefix}_growth_n (sample count)."""
    yearly = (df[[group_col, 't1_year', 'log_change']].dropna()
              .groupby([group_col, 't1_year'])
              .agg(sum_lc=('log_change', 'sum'),
                   n_lc=('log_change', 'size'))
              .reset_index()
              .sort_values([group_col, 't1_year']))
    yearly['cum_sum'] = yearly.groupby(group_col)['sum_lc'].cumsum()
    yearly['cum_n']   = yearly.groupby(group_col)['n_lc'].cumsum()
    lookup = yearly.rename(columns={'t1_year': 'lookup_year'})[
        [group_col, 'lookup_year', 'cum_sum', 'cum_n']].sort_values('lookup_year')

    tmp = pd.DataFrame({
        group_col: df[group_col].values,
        'lookup_year': (df['snapshot_year'] - 1).astype('int64').values,
        '__order__': np.arange(len(df)),
    }).sort_values('lookup_year')
    merged = pd.merge_asof(
        tmp, lookup, on='lookup_year', by=group_col, direction='backward',
    ).sort_values('__order__')

    cum_sum = merged['cum_sum'].fillna(0).values
    cum_n   = merged['cum_n'].fillna(0).values
    with np.errstate(invalid='ignore', divide='ignore'):
        growth = np.where(cum_n > 0, cum_sum / np.maximum(cum_n, 1), np.nan)
    df[f'{out_prefix}_growth']   = growth
    df[f'{out_prefix}_growth_n'] = cum_n
    fill = float(np.nanmean(df[f'{out_prefix}_growth'])) if df[f'{out_prefix}_growth'].notna().any() else 0.0
    df[f'{out_prefix}_growth']   = df[f'{out_prefix}_growth'].fillna(fill)
    df[f'{out_prefix}_growth_n'] = df[f'{out_prefix}_growth_n'].fillna(0)

_add_expanding_momentum(df, 'city_name_enc', 'city_recent')

# This is used to calc market trends and check the model's efficiency. 
# DO NOT SEND to the predict function
# df['annual_growth'] = (df['price_t1'] / df['price_t0'])**(1 / df['horizon_years']) - 1
past_data = df[df['t1_year'] <= cutoff]
# momentum_library = past_data.groupby(['city_name', 'snapshot_year'])['annual_growth'].mean().reset_index()
# momentum_library['market_momentum'] = momentum_library.groupby('city_name')['annual_growth'].shift(1)
# df = df.merge(momentum_library[['city_name', 'snapshot_year', 'market_momentum']], 
#                            on=['city_name', 'snapshot_year'], how='left')
# df = df.dropna(subset=['market_momentum'])


score_now_cols = [c for c in df.columns if '_score_now' in c]
score_future_cols = [c for c in df.columns if '_score_future' in c]

delta_features = []
for now_col in score_now_cols:
    base_name = now_col.replace('_score_now', '')
    fut_col = f"{base_name}_score_future"
    delta_col = f"{base_name}_delta"
    df[delta_col] = ( df[fut_col] - df[now_col] )
    delta_features.append(delta_col)

# Geography + property structurals + temporal context. snapshot_year lets the
# model condition on macro era; lat/lon give finer spatial signal than the
# noisy city code alone. horizon_years is now a feature because we pool all
# horizons into a single model (target is annualised log return, see below).
base_features = [
    "city_name_enc", "property_type_enc",
    "snapshot_year", "horizon_years", "lat", "lon",
    "num_rooms", "building_year", "building_floors",
    "log_price_t0", "national_log_price_year",
    "property_age",
    "city_recent_growth", "city_recent_growth_n",
] + distance_features
common_features = base_features + delta_features + score_now_cols

base_hyperparams = dict(
    # Pseudo-Huber: behaves like MSE near zero, like MAE in the tails. Robust
    # to the multi-x growth outliers that still survive winsorisation, without
    # discarding them. huber_slope sets the L2->L1 transition point on the
    # (log-change residual) scale; 0.5 ≈ a 65% price move.
    objective="reg:pseudohubererror",
    huber_slope=0.5,
    n_estimators=2000,
    learning_rate=0.05,
    max_depth=6,
    reg_alpha=0.0,
    reg_lambda=1.0,
    colsample_bytree=0.8,
    subsample=0.8,
    early_stopping_rounds=100,
)

# log_change = ln(price_t1 / price_t0). Additive across time, symmetric, and
# robust to multi-x growth outliers that blow up pct_change RMSE. We convert
# predictions back to pct for the downstream clustering / DB write.
TARGET = 'log_change'

for col in score_now_cols + delta_features:
    df[col] = pd.to_numeric(df[col], errors='coerce')


def train_and_evaluate(df, cutoff, val_time, features, hyperparams, verbose=True):
    """Train ONE pooled model across all horizons and evaluate per-horizon.

    Target = annualised log return (log_change / horizon_years). Pooling lets
    the 10y horizon borrow strength from the much larger 5y sample, and the
    annualisation puts every row on a comparable per-year scale so the model
    can learn shared return dynamics. `horizon_years` is also a feature, so
    the model can still adjust for horizon-specific effects.

    Returns:
        per_horizon_metrics: list[dict] one row per horizon
        future_df: predictions DataFrame for test rows (snapshot<=cutoff, t1>cutoff)
        model: the fitted XGBRegressor (for inspection / feature importance)
    """
    train_val_df = df[df['t1_year'] <= cutoff].copy()
    train_df = train_val_df[train_val_df['t1_year'] < (cutoff - val_time)].copy()
    val_df   = train_val_df[train_val_df['t1_year'] >= (cutoff - val_time)].copy()
    future_df = df[(df['snapshot_year'] <= cutoff) & (df['t1_year'] > cutoff)].copy()

    train_df = train_df.dropna(subset=features + ['log_change', 'horizon_years'])
    val_df   = val_df.dropna(subset=features + ['log_change', 'horizon_years'])
    future_df = future_df.dropna(subset=features + ['log_change', 'horizon_years'])

    # Annualised log return: this is the actual training target. Putting 5y
    # and 10y on the same per-year scale is what makes pooling sound.
    for d in (train_df, val_df, future_df):
        d['ann_log_change'] = d['log_change'] / d['horizon_years']

    # Winsorise the annualised target on train only (kills 4x/10y type rows).
    if len(train_df) > 0:
        lo, hi = train_df['ann_log_change'].quantile(0.02), train_df['ann_log_change'].quantile(0.98)
        train_df = train_df[train_df['ann_log_change'].between(lo, hi)].copy()

    if len(train_df) == 0 or len(val_df) == 0 or len(future_df) == 0:
        return [], pd.DataFrame(), None

    # City/year baseline computed on the annualised target from TRAIN only.
    cy_mean = (train_df.groupby(['city_name_enc', 'snapshot_year'])['ann_log_change']
                       .mean().rename('cy_mean').reset_index())
    global_mean = float(train_df['ann_log_change'].mean())

    for d in (train_df, val_df, future_df):
        d.drop(columns=['cy_mean'], errors='ignore', inplace=True)
    train_df = train_df.merge(cy_mean, on=['city_name_enc', 'snapshot_year'], how='left')
    val_df   = val_df.merge(cy_mean,   on=['city_name_enc', 'snapshot_year'], how='left')
    future_df = future_df.merge(cy_mean, on=['city_name_enc', 'snapshot_year'], how='left')
    for d in (train_df, val_df, future_df):
        d['cy_mean'] = d['cy_mean'].fillna(global_mean)
        d['y_resid'] = d['ann_log_change'] - d['cy_mean']

    model = xgb.XGBRegressor(**hyperparams, base_score=0.0)
    model.fit(train_df[features], train_df['y_resid'],
              eval_set=[(val_df[features], val_df['y_resid'])], verbose=False)

    # Predict annualised residual -> add baseline -> multiply by horizon to
    # recover log_change in the original (multi-year) scale.
    pred_resid = model.predict(future_df[features])
    future_df['pred_ann_log_change'] = pred_resid + future_df['cy_mean']
    future_df['pred_log_change'] = future_df['pred_ann_log_change'] * future_df['horizon_years']
    future_df['pred_pct_change'] = np.expm1(future_df['pred_log_change'])

    if verbose:
        print(f"\n[cutoff={cutoff}] pooled train={len(train_df)} val={len(val_df)} test={len(future_df)}")
        imp = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
        print(f"  Top 8 features: {list(imp.head(8).index)}")

    per_horizon_metrics = []
    for horizon in sorted(future_df['horizon_years'].unique()):
        sub = future_df[future_df['horizon_years'] == horizon]
        if len(sub) == 0:
            continue
        y_true = sub['log_change']
        y_pred = sub['pred_log_change']
        mae   = mean_absolute_error(y_true, y_pred)
        medae = float(np.median(np.abs(y_true - y_pred)))
        rmse  = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        r2    = r2_score(y_true, y_pred)
        per_horizon_metrics.append({
            'cutoff': cutoff, 'horizon_years': int(horizon),
            'n_test': len(sub),
            'mae_log': mae, 'medae_log': medae, 'rmse_log': rmse, 'r2_log': r2,
        })
        if verbose:
            print(f"  h={int(horizon)}y  n={len(sub):>6}  "
                  f"log-MAE={mae:.4f}  MedAE={medae:.4f}  RMSE={rmse:.4f}  R²={r2:.4f}")

    return per_horizon_metrics, future_df, model


# --- Multi-cutoff time-series CV ---
# Train+evaluate at several historical cutoffs and average the metrics. A
# single fold at one cutoff is noisy; averaging across eras gives honest
# error bars and reveals whether the model degrades in any particular regime.
cv_cutoffs = [2014, 2016, 2018, 2020]
production_cutoff = cutoff   # the one whose predictions get saved to the DB

print(f"\n=== Multi-cutoff CV over {cv_cutoffs} ===")
cv_rows = []
for c in cv_cutoffs:
    rows, _, _ = train_and_evaluate(df, c, val_time, common_features, base_hyperparams, verbose=True)
    cv_rows.extend(rows)

cv_df = pd.DataFrame(cv_rows)
print("\n--- CV per (cutoff, horizon) ---")
print(cv_df.to_string(index=False))
print("\n--- CV averaged across cutoffs, per horizon ---")
print(cv_df.groupby('horizon_years')[['mae_log', 'medae_log', 'rmse_log', 'r2_log']]
            .mean().round(4).to_string())

# --- Production run at the chosen cutoff ---
# These are the predictions we actually save to the DB for the UI.
print(f"\n=== Production run at cutoff={production_cutoff} ===")
per_horizon_metrics, future_df, _ = train_and_evaluate(
    df, production_cutoff, val_time, common_features, base_hyperparams, verbose=True
)


# Cluster Results — geography only. Mixing lat/lon with pred_pct_change after
# StandardScaler made the cluster geometry depend on the spread of predictions,
# which is not what we want. eps is in degrees here (~1.1 km at Israel's lat).
cluster_coords = future_df[['lat', 'lon']].values
db = DBSCAN(eps=0.01, min_samples=12).fit(cluster_coords)
future_df['cluster'] = db.labels_

polygons = []
for cid in np.unique(db.labels_):
    if cid == -1: continue # Skip noise
    
    # Get all points in this cluster
    cluster_mask = future_df['cluster'] == cid
    subset = future_df[cluster_mask]
    
    pts = subset[['lon', 'lat']].values
    hull = MultiPoint(pts).convex_hull
    
    polygons.append({
        'cluster_id': int(cid),
        'avg_growth': float(subset['pred_pct_change'].mean()),
        'certainty': float(1 / (1 + subset['pred_pct_change'].std()) if subset['pred_pct_change'].std() > 0 else 1.0),
        'wkt': hull.wkt
    })

# Save to DB

insert_query = """
        INSERT INTO public.growth_clusters (cluster_id, avg_growth, certainty, geom)
        VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326));
    """

data_to_insert = [
    (p['cluster_id'], p['avg_growth'], p['certainty'], p['wkt']) 
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
    print("starting insertion")
    cur.executemany(insert_query, data_to_insert)
    conn.commit()
    print(f"Successfully saved {len(data_to_insert)} clusters to the database.") 
except Exception as e:
        print(f"Database error: {e}")

cur.close()
conn.close()
