import psycopg
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.cluster import DBSCAN
from shapely.geometry import MultiPoint
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

cutoff = 2015
val_time = 1

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
le = LabelEncoder()
df['property_type_enc'] = le.fit_transform(df['property_type'])
df['city_name_enc'] = le.fit_transform(df['city_name'])

# This is used to calc market trends and check the model's efficiency. 
# DO NOT SEND to the predict function
df['annual_growth'] = (df['price_t1'] / df['price_t0'])**(1 / df['horizon_years']) - 1
past_data = df[df['t1_year'] <= cutoff]
momentum_library = past_data.groupby(['city_name', 'snapshot_year'])['annual_growth'].mean().reset_index()
momentum_library['market_momentum'] = momentum_library.groupby('city_name')['annual_growth'].shift(1)
df = df.merge(momentum_library[['city_name', 'snapshot_year', 'market_momentum']], 
                           on=['city_name', 'snapshot_year'], how='left')
df = df.dropna(subset=['market_momentum'])


score_now_cols = [c for c in df.columns if '_score_now' in c]
score_future_cols = [c for c in df.columns if '_score_future' in c]

delta_features = []
for now_col in score_now_cols:
    base_name = now_col.replace('_score_now', '')
    fut_col = f"{base_name}_score_future"
    delta_col = f"{base_name}_delta"
    df[delta_col] = ( df[fut_col] - df[now_col] )
    delta_features.append(delta_col)

base_features = ["market_momentum", "city_name_enc"]
final_features = base_features + delta_features + score_now_cols

for col in score_now_cols + delta_features:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Splitting data to classes
train_val_df = df[df['t1_year'] <= cutoff].copy()
train_df = train_val_df[train_val_df['t1_year'] < (cutoff - val_time)].copy()
val_df   = train_val_df[train_val_df['t1_year'] >= (cutoff - val_time)].copy()
future_df = df[(df['snapshot_year'] <= cutoff) & (df['t1_year'] > cutoff)].copy()

train_df = train_df[train_df['annual_growth'].between(train_df['annual_growth'].quantile(0.02), 
                                                    train_df['annual_growth'].quantile(0.98))].copy()

train_df = train_df.dropna(subset=final_features)
val_df = val_df.dropna(subset=final_features)
future_df = future_df.dropna(subset=final_features)

X_train = train_df[final_features]
y_train = train_df['annual_growth']
X_val = val_df[final_features]
Y_val = val_df['annual_growth']

# Check data distribution
print("train size", len(train_df))
print("val size", len(val_df))
print("test size", len(future_df))

model = xgb.XGBRegressor(
    n_estimators=300, 
    learning_rate=0.01,
    max_depth=3,
    reg_alpha=5,
    reg_lambda=15,
    colsample_bytree=0.4,
    subsample=0.6,
    early_stopping_rounds=30,
    base_score=train_df['annual_growth'].mean()
)
model.fit(
    X_train, y_train,
    eval_set=[(X_val, Y_val)],
    verbose=False
)

X_future = future_df[final_features].copy()
future_df['pred_annual_growth'] = model.predict(X_future[final_features])

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# --- MODEL EVALUATION ---
mae = mean_absolute_error(future_df['annual_growth'], future_df['pred_annual_growth'])
rmse = np.sqrt(mean_squared_error(future_df['annual_growth'], future_df['pred_annual_growth']))
r2 = r2_score(future_df['annual_growth'], future_df['pred_annual_growth'])

print("\n--- Model Performance Metrics (Post-2014) ---")
print(f"Mean Absolute Error (MAE): {mae:.4%}") 
print(f"Root Mean Squared Error (RMSE): {rmse:.4%}")
print(f"R-squared Score (R²): {r2:.4f}")

importances = pd.Series(model.feature_importances_, index=final_features).sort_values(ascending=False)
print("\n--- Top 5 Most Influential Features ---")
print(importances.head(5))

# Cluster Results
cluster_scaled = StandardScaler().fit_transform(future_df[['lat', 'lon', 'pred_annual_growth']])
db = DBSCAN(eps=0.4, min_samples=12).fit(cluster_scaled)
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
        'avg_growth': float(subset['pred_annual_growth'].mean()),
        'certainty': float(1 / (1 + subset['pred_annual_growth'].std()) if subset['pred_annual_growth'].std() > 0 else 1.0),
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
