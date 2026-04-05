from etl.common.db import get_conn
from etl.common.paths import PROCESSED_DIR
import io
import pandas as pd

POI_CSV_PATH = PROCESSED_DIR / "pois_for_db.csv"

def to_int_or_none(x):
    if pd.isna(x):
        return None
    try:
        return int(float(x))
    except:
        return None

def main():
    df = pd.read_csv(POI_CSV_PATH, encoding="utf-8-sig")

    # Expected columns: poi_id, poi_type, geom_wkt, name_en, name_he, opening_year
    df["opening_year"] = df["opening_year"].apply(to_int_or_none)

    # Rename to match staging columns
    df = df.rename(columns={
        "poi_id": "poi_uuid",
        "poi_type": "poi_type_id",
    })

    needed = ["poi_uuid", "poi_type_id", "geom_wkt", "name_en", "name_he", "opening_year"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1) staging table
            cur.execute("""
                CREATE TEMP TABLE stg_poi_current (
                    poi_uuid UUID,
                    poi_type_id SMALLINT,
                    geom_wkt TEXT,
                    name_en TEXT,
                    name_he TEXT,
                    opening_year TEXT
                ) ON COMMIT DROP;
            """)

            # 2) COPY into staging (very fast)
            buf = io.StringIO()
            df[needed].to_csv(buf, index=False, header=False)
            buf.seek(0)
            cur.copy_expert(
                "COPY stg_poi_current (poi_uuid, poi_type_id, geom_wkt, name_en, name_he, opening_year) "
                "FROM STDIN WITH (FORMAT csv)",
                buf
            )

            # 3) upsert into final table
            cur.execute("""
                INSERT INTO poi_current (poi_uuid, poi_type_id, geom, name_en, name_he, opening_year)
                SELECT
                    poi_uuid,
                    poi_type_id,
                    ST_SetSRID(ST_GeomFromText(geom_wkt), 4326)::geometry(Point,4326),
                    NULLIF(BTRIM(name_en), ''),
                    NULLIF(BTRIM(name_he), ''),
                    CASE
                    WHEN NULLIF(BTRIM(opening_year), '') IS NULL THEN NULL
                    ELSE CAST(CAST(opening_year AS NUMERIC) AS INT)
                    END::SMALLINT
                FROM stg_poi_current
                ON CONFLICT (poi_uuid) DO UPDATE
                SET
                    poi_type_id  = EXCLUDED.poi_type_id,
                    geom         = EXCLUDED.geom,
                    name_en      = EXCLUDED.name_en,
                    name_he      = EXCLUDED.name_he,
                    opening_year = EXCLUDED.opening_year;
            """)

        conn.commit()

    print(f"✅ Uploaded {len(df):,} POIs into poi_current")

if __name__ == "__main__":
    main()