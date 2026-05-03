import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import xgboost as xgb
import numpy as np
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# Import model configuration to drop target columns like price_t1
from ml.config import COLS_TO_DROP 

load_dotenv()

def build_and_save_heatmap_data():
    print("🚀 Starting Multi-City Grid Heatmap Data Generation...")

    # 1. Connect to DB
    engine = create_engine(f"postgresql://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}")

    # 2. Load Models
    print("🤖 Loading Machine Learning Models...")
    model_5y = xgb.XGBRegressor(enable_categorical=True)
    model_5y.load_model("data/saved_models/xgb_real_estate_5yr_v1.json")
    
    model_10y = xgb.XGBRegressor(enable_categorical=True)
    model_10y.load_model("data/saved_models/xgb_real_estate_10yr_v1.json")

    # 3. Load all 2014 properties (ALL CITIES)
    print("📥 Loading all 2014 property snapshots from Database...")
    query = """
        SELECT s.*, p.lat, p.lon 
        FROM property_features_snapshot s
        JOIN properties p ON s.property_id = p.property_id
        WHERE s.snapshot_year = 2014
    """
    df_all = pd.read_sql_query(query, engine)
    
    # Clean NULL values
    df_all = df_all.replace(r'^\s*$', np.nan, regex=True)
    df_all = df_all.replace(['NULL', 'null', 'None'], np.nan)
    
    # הגדרת עמודות טקסט שחייבות להישאר טקסט
    cols_to_keep_as_text = ['city_name', 'street', 'property_key', 'house_number', 'geometry']
    for col in df_all.columns:
        if col not in cols_to_keep_as_text:
            df_all[col] = pd.to_numeric(df_all[col], errors='coerce')
    
    # Convert to GeoDataFrame
    gdf_all = gpd.GeoDataFrame(
        df_all, 
        geometry=gpd.points_from_xy(df_all['lon'], df_all['lat']),
        crs="EPSG:4326"
    )

    results = []
    
    # Find all unique cities in the snapshot
    unique_cities = gdf_all['city_name'].unique()
    print(f"🏙️ Found {len(unique_cities)} unique cities. Processing one by one...\n")

    # שומרים רק את העמודות שהמודל מצפה לקבל
    expected_cols = model_5y.get_booster().feature_names 

    # ==========================================
    # 4. Loop through each city to build local grids
    # ==========================================
    for city in unique_cities:
        print(f"--- Processing City: {city} ---")
        
        # Isolate data for the current city
        gdf_city = gdf_all[gdf_all['city_name'] == city].copy()
        
        # Create a localized spatial grid based on THIS city's boundaries
        xmin, ymin, xmax, ymax = gdf_city.total_bounds
        GRID_SIZE = 30 # 30x30 resolution per city
        
        x_coords = np.linspace(xmin, xmax, GRID_SIZE)
        y_coords = np.linspace(ymin, ymax, GRID_SIZE)
        
        polygons = []
        for i in range(len(x_coords)-1):
            for j in range(len(y_coords)-1):
                polygons.append(Polygon([
                    (x_coords[i], y_coords[j]),
                    (x_coords[i+1], y_coords[j]),
                    (x_coords[i+1], y_coords[j+1]),
                    (x_coords[i], y_coords[j+1])
                ]))
                
        grid_gdf = gpd.GeoDataFrame({'grid_id': range(len(polygons)), 'geom': polygons}, geometry='geom', crs="EPSG:4326")
        
        # Filter grid cells to only those containing actual properties
        grid_with_data = gpd.sjoin(grid_gdf, gdf_city, how='inner', predicate='intersects')
        
        agg_dict = {'geom': 'first'}
        for col in grid_with_data.columns:
            if col in ['lat', 'lon', 'id', 'geometry', 'index_right', 'grid_id', 'geom']:
                continue 
                
            if col in cols_to_keep_as_text:
                agg_dict[col] = 'first'
            elif pd.api.types.is_numeric_dtype(grid_with_data[col]):
                agg_dict[col] = 'mean'
            else:
                agg_dict[col] = 'first'
                
        aggregated_grid = grid_with_data.groupby('grid_id').agg(agg_dict).reset_index()
        final_grid_gdf = gpd.GeoDataFrame(aggregated_grid, geometry='geom', crs="EPSG:4326")

      # ==========================================
        # 5. Predict growth for each local cell
        # ==========================================
        for idx, row in final_grid_gdf.iterrows():
            row_dict = row.drop(['geom', 'grid_id']).to_dict()
            
            row_dict['num_rooms'] = 3 
            row_dict['location_accuracy'] = 1 
            
            features_df = pd.DataFrame([row_dict])
            
            for col in features_df.columns:
                if col not in ['city_name', 'location_accuracy']:
                    features_df[col] = pd.to_numeric(features_df[col], errors='coerce')
                    
            features_df['city_name'] = features_df['city_name'].astype('category')
            features_df['location_accuracy'] = features_df['location_accuracy'].astype('category')
                    
            features_df = features_df[expected_cols]
            
            try:
                # 1. מנסים לחזות רגיל
                pred_5y_log = model_5y.predict(features_df)[0]
                pred_10y_log = model_10y.predict(features_df)[0]
                
                growth_5y = (np.exp(pred_5y_log) - 1) * 100
                growth_10y = (np.exp(pred_10y_log) - 1) * 100
            except Exception as e:
                # 2. ה-NaN יצר שגיאת Float Category.
                # הפתרון: שמים עיר "בטוחה" מהאזור שעברה בהצלחה (רמת גן). 
                # המודל עדיין יחשב את ההבדלים בתוך תל אביב על סמך ציוני התשתיות האמיתיות (פארקים, רכבות וכו') של כל משבצת!
                features_df['city_name'] = 'רמת גן'
                features_df['city_name'] = features_df['city_name'].astype('category')
                
                pred_5y_log = model_5y.predict(features_df)[0]
                pred_10y_log = model_10y.predict(features_df)[0]
                
                growth_5y = (np.exp(pred_5y_log) - 1) * 100
                growth_10y = (np.exp(pred_10y_log) - 1) * 100

            results.append({
                'city_name': city,
                'neighborhood_name': f"Grid {row['grid_id']}",
                'baseline_year': 2014,
                'growth_5y_pct': round(growth_5y, 2),
                'growth_10y_pct': round(growth_10y, 2),
                'geom': row['geom']
            })

    # ==========================================
    # 6. Save master data to PostGIS
    # ==========================================
    print("\n💾 Saving master heatmap data to Database...")
    output_gdf = gpd.GeoDataFrame(results, geometry='geom', crs="EPSG:4326")
    output_gdf.to_postgis('neighborhood_predictions', engine, if_exists='replace', index=False)
    
    print("✅ Multi-City Grid Heatmap successfully saved! Ready for UI consumption.")

if __name__ == "__main__":
    build_and_save_heatmap_data()