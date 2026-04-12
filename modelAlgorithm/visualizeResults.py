import psycopg
import pandas as pd
import matplotlib.pyplot as plt

conn = psycopg.connect(
    host="10.10.248.102",
    port=5432,
    dbname="trendsense",
    user="postgres",
    password="Aa123456",
)

poly_df = pd.read_sql_query("""
                            SELECT cluster_id, avg_growth, certainty, ST_AsText(geom) as geom
                            FROM public.growth_clusters;
                            """, conn)

conn.close()

# Visualize

import geopandas as gpd
from shapely import wkt
import matplotlib.pyplot as plt

# 1. Convert your results into a GeoDataFrame
# Assuming 'poly_df' is your DataFrame containing the 'geom' column
poly_df['geometry'] = poly_df['geom'].apply(wkt.loads)
gdf = gpd.GeoDataFrame(poly_df, geometry='geometry')

# 2. Plotting the actual polygons
fig, ax = plt.subplots(figsize=(12, 8))

# Plot the polygons colored by growth
gdf.plot(
    column='avg_growth', 
    cmap='RdYlGn', 
    legend=True, 
    alpha=0.6, 
    edgecolor='black', 
    ax=ax,
    legend_kwds={'label': "Predicted Annual Growth (%)"}
)

# 3. Add labels for the Cluster IDs
for idx, row in gdf.iterrows():
    # Use the centroid of the polygon to place the text label
    plt.annotate(
        text=f"ID: {row['cluster_id']}", 
        xy=(row['geometry'].centroid.x, row['geometry'].centroid.y),
        horizontalalignment='center',
        fontsize=8,
        fontweight='bold'
    )

plt.title("Spatial Hotspots: Geographic Cluster Growth")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.grid(True, alpha=0.2)
plt.show()
