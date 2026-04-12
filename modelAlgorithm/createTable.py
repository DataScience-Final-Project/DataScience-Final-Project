import psycopg
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

conn = psycopg.connect(
    host="10.10.248.102",
    port=5432,
    dbname="trendsense",
    user="postgres",
    password="Aa123456",
)

cur = conn.cursor()
QUERY = """
CREATE TABLE IF NOT EXISTS public.growth_clusters (
                    id SERIAL PRIMARY KEY,
                    cluster_id INTEGER,
                    avg_growth FLOAT8,
                    certainty FLOAT8,
                    geom GEOMETRY(Polygon, 4326),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
"""


cur.execute(QUERY)
cur.execute("CREATE INDEX IF NOT EXISTS idx_growth_clusters_geom ON public.growth_clusters USING GIST(geom);")
conn.commit()
print("Table 'growth_clusters' created successfully.")

cur.close()
conn.close()