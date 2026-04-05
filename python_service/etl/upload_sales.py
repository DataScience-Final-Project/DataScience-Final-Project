import io
import re
import pandas as pd
from pathlib import Path

from etl.common.db import get_conn
from etl.common.paths import PROCESSED_DIR

CSV_PATH = Path(PROCESSED_DIR) / "sales_output.csv"
HOUSE_NUM_RE = re.compile(r"(\d{1,5})")

def extract_house_number(s: str):
    if not s:
        return None
    m = HOUSE_NUM_RE.search(str(s))
    return m.group(1) if m else None

def main():
    print("📥 Loading CSV...")
    df = pd.read_csv(CSV_PATH, low_memory=False, encoding="utf-8-sig")

    print("🧹 Cleaning...")
    df["DEALAMOUNT"] = (
        df["DEALAMOUNT"].astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(".0", "", regex=False)
    )
    df["DEALAMOUNT"] = pd.to_numeric(df["DEALAMOUNT"], errors="coerce")
    df["DEALDATETIME"] = pd.to_datetime(df["DEALDATETIME"], errors="coerce")
    df["house_number"] = df["DISPLAYADRESS"].apply(extract_house_number)

    for col in ["BUILDINGYEAR", "BUILDINGFLOORS", "TYPE", "ASSETROOMNUM"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["lat", "lon"])

    # geom EWKT
    if "geom" not in df.columns or df["geom"].isna().all():
        df["geom"] = "SRID=4326;POINT(" + df["lon"].astype(str) + " " + df["lat"].astype(str) + ")"

    # Create a true property key based on physical location and size (Gush-Helka + Rooms)
    df["property_key"] = df["city_name"].astype(str).fillna("") + "|" + df["POLYGON_ID"].astype(str).fillna("") + "|rooms:" + df["ASSETROOMNUM"].astype(str).fillna("0")

    stg = df[[
        "property_key", "city_name", "street", "house_number",
        "lat", "lon", "geom",
        "ASSETROOMNUM", "BUILDINGYEAR", "BUILDINGFLOORS", "TYPE",
        "DEALDATETIME", "DEALAMOUNT"
    ]].copy().rename(columns={
        "ASSETROOMNUM": "num_rooms",
        "BUILDINGYEAR": "building_year",
        "BUILDINGFLOORS": "building_floors",
        "TYPE": "property_type",
        "DEALDATETIME": "sale_datetime",
        "DEALAMOUNT": "sale_price",
        "geom": "geom_ewkt",
    })

    print(f"✅ Rows to load: {len(stg):,}")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # TEMP staging
            cur.execute("""
                CREATE TEMP TABLE stg_sales (
                  property_key TEXT,
                  city_name TEXT,
                  street TEXT,
                  house_number TEXT,
                  lat DOUBLE PRECISION,
                  lon DOUBLE PRECISION,
                  geom_ewkt TEXT,
                  num_rooms DOUBLE PRECISION,
                  building_year TEXT,
                  building_floors TEXT,
                  property_type TEXT,
                  sale_datetime TIMESTAMP,
                  sale_price TEXT
                ) ON COMMIT DROP;
            """)

            # COPY from pandas -> temp
            buf = io.StringIO()
            stg.to_csv(buf, index=False, header=False)
            buf.seek(0)
            cur.copy_expert("""
                COPY stg_sales (
                  property_key, city_name, street, house_number,
                  lat, lon, geom_ewkt,
                  num_rooms, building_year, building_floors, property_type,
                  sale_datetime, sale_price
                )
                FROM STDIN WITH (FORMAT csv)
            """, buf)

            # Ensure property_key exists + unique
            cur.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS property_key TEXT;")
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS properties_property_key_uk
                ON properties(property_key);
            """)

            # Upsert properties
            cur.execute("""
                INSERT INTO properties (
                property_key, city_name, street, house_number,
                lat, lon, geom,
                num_rooms, building_year, building_floors, property_type
                )
                SELECT DISTINCT ON (property_key)
                property_key,
                NULLIF(BTRIM(city_name),''),
                NULLIF(BTRIM(street),''),
                NULLIF(BTRIM(house_number),''),
                lat, lon,
                ST_GeomFromEWKT(geom_ewkt),
                num_rooms,
                CASE WHEN NULLIF(BTRIM(building_year),'') IS NULL THEN NULL
                    ELSE CAST(CAST(building_year AS NUMERIC) AS INT)
                END,
                CASE WHEN NULLIF(BTRIM(building_floors),'') IS NULL THEN NULL
                    ELSE CAST(CAST(building_floors AS NUMERIC) AS INT)
                END,
                CASE WHEN NULLIF(BTRIM(property_type),'') IS NULL THEN NULL
                    ELSE CAST(CAST(property_type AS NUMERIC) AS INT)
                END
                FROM stg_sales
                WHERE property_key IS NOT NULL AND BTRIM(property_key) <> ''
                AND lat IS NOT NULL AND lon IS NOT NULL
                ON CONFLICT (property_key) DO UPDATE
                SET
                city_name = COALESCE(EXCLUDED.city_name, properties.city_name),
                street = COALESCE(EXCLUDED.street, properties.street),
                house_number = COALESCE(EXCLUDED.house_number, properties.house_number),
                lat = COALESCE(EXCLUDED.lat, properties.lat),
                lon = COALESCE(EXCLUDED.lon, properties.lon),
                geom = COALESCE(EXCLUDED.geom, properties.geom),
                num_rooms = COALESCE(EXCLUDED.num_rooms, properties.num_rooms),
                building_year = COALESCE(EXCLUDED.building_year, properties.building_year),
                building_floors = COALESCE(EXCLUDED.building_floors, properties.building_floors),
                property_type = COALESCE(EXCLUDED.property_type, properties.property_type);
            """)

            # Unique index for transactions to avoid duplicates
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS transactions_uk
                ON transactions(property_id, sale_date, sale_price);
            """)

            # Insert transactions
            cur.execute("""
                INSERT INTO transactions (property_id, sale_date, sale_price)
                SELECT
                p.property_id,
                s.sale_datetime::date,
                CAST(CAST(s.sale_price AS NUMERIC) AS BIGINT)
                FROM stg_sales s
                JOIN properties p
                ON p.property_key = s.property_key
                WHERE s.sale_datetime IS NOT NULL
                AND NULLIF(BTRIM(s.sale_price),'') IS NOT NULL
                ON CONFLICT DO NOTHING;
            """)

        conn.commit()

    print("🎉 DONE: properties + transactions loaded.")

if __name__ == "__main__":
    main()