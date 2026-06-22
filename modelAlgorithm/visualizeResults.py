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
                            SELECT cluster_id, horizon_years, avg_growth, certainty, ST_AsText(geom) as geom
                            FROM public.growth_clusters;
                            """, conn)

conn.close()

# Visualize

import geopandas as gpd
from shapely import wkt
from shapely.geometry import Point
import matplotlib.pyplot as plt

# 1. Convert your results into a GeoDataFrame
# Assuming 'poly_df' is your DataFrame containing the 'geom' column
poly_df['geometry'] = poly_df['geom'].apply(wkt.loads)
gdf = gpd.GeoDataFrame(poly_df, geometry='geometry')

# 2. Plotting the actual polygons (map on the left, info panel on the right)
fig, (ax, ax_info) = plt.subplots(
    1, 2, figsize=(15, 8), gridspec_kw={"width_ratios": [3, 1]}
)

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
    ax.annotate(
        text=f"ID: {row['cluster_id']}", 
        xy=(row['geometry'].centroid.x, row['geometry'].centroid.y),
        horizontalalignment='center',
        fontsize=8,
        fontweight='bold'
    )

ax.set_title("Spatial Hotspots: Geographic Cluster Growth")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.grid(True, alpha=0.2)

# 4. Side info panel: shows the data of the polygon(s) you click on
ax_info.axis("off")
info_text = ax_info.text(
    0.0, 1.0, "Click a polygon to see its data",
    va="top", ha="left", fontsize=10, family="monospace",
    transform=ax_info.transAxes,
)

_highlights = []  # boundary lines drawn for the currently selected polygon(s)


def _format_row(row):
    horizon = row.get("horizon_years", "N/A")
    return (
        f"Cluster ID : {row['cluster_id']}\n"
        f"Horizon    : {horizon} yrs\n"
        f"Avg Growth : {row['avg_growth']:.4f}\n"
        f"Certainty  : {row['certainty']:.4f}"
    )


def _highlight(geom):
    xs, ys = geom.exterior.xy
    line, = ax.plot(xs, ys, color="blue", linewidth=2.5, zorder=5)
    _highlights.append(line)


def on_click(event):
    # ignore clicks outside the map (e.g. on the info panel or toolbar)
    if event.inaxes != ax or event.xdata is None or event.ydata is None:
        return

    pt = Point(event.xdata, event.ydata)
    hits = gdf[gdf.contains(pt)]

    # clear previous selection highlights
    for line in _highlights:
        line.remove()
    _highlights.clear()

    if hits.empty:
        info_text.set_text("No polygon here.\nClick inside a hotspot.")
    else:
        sep = "\n" + "-" * 26 + "\n"
        blocks = []
        for _, row in hits.iterrows():
            blocks.append(_format_row(row))
            _highlight(row["geometry"])
        header = f"{len(hits)} polygon(s) at this point:\n" + "=" * 26 + "\n"
        info_text.set_text(header + sep.join(blocks))

    fig.canvas.draw_idle()


fig.canvas.mpl_connect("button_press_event", on_click)

plt.tight_layout()
plt.show()
