import pandas as pd
import geopandas as gpd
from pathlib import Path

# ייבוא נתיב התיקייה של המכירות שלך (כמו בקוד המקורי)
try:
    from etl.common.paths import SALES_DIR, SHAPE_DIR, PROCESSED_DIR
except ImportError:
    from common.paths import SALES_DIR, SHAPE_DIR, PROCESSED_DIR

SALES_DIR = Path(SALES_DIR)
# שים כאן את הנתיב לתיקייה שבה שמת את קבצי ה-Shapefile שהורדת
OUTPUT_CSV = Path(PROCESSED_DIR, 'sales_output.csv')

def main():
    # קריאת כל 20 קבצי האקסל מתיקיית המכירות
    files = sorted(SALES_DIR.glob("*.xlsx"))
    if not files:
        print("❌ No excel files found!")
        return

    print(f"📦 Reading {len(files)} XLSX files...")
    df_sales = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
    print(f"📄 Loaded {len(df_sales):,} total sales records.")

    # נוודא שאין רווחים מיותרים בעמודת ה-POLYGON_ID (הגוש-חלקה)
    df_sales['POLYGON_ID'] = df_sales['POLYGON_ID'].astype(str).str.strip()

    # קריאת מפת החלקות של ישראל
    print(f"\n🗺️ Loading Israel Parcels Shapefile (this will take 1-2 minutes)...")
    try:
        parcels_gdf = gpd.read_file(SHAPE_DIR)
    except Exception as e:
        print(f"❌ Failed to load Shapefile: {e}")
        return

    # יצירת מזהה זהה לקובץ המכירות (גוש-חלקה)
    print("⚙️ Processing coordinates...")

    # בדרך כלל בקבצי מפ"י העמודות נקראות GUSH_NUM ו- PARCEL
    # אם השמות שונים, נדפיס אותם כדי שנוכל לתקן
    if 'GUSH_NUM' not in parcels_gdf.columns or 'PARCEL' not in parcels_gdf.columns:
        print("⚠️ Column names in shapefile are different! Here are the available columns:")
        print(parcels_gdf.columns.tolist())
        return

    # חיבור גוש וחלקה עם מקף כדי שיתאים בדיוק ל- POLYGON_ID בקובץ שלך (למשל "6144-626")
    parcels_gdf['MATCH_ID'] = parcels_gdf['GUSH_NUM'].astype(str).str.strip() + '-' + parcels_gdf['PARCEL'].astype(
        str).str.strip()

    # המרת קואורדינטות מ-ITM (ישראל) ל-WGS84 (GPS עולמי)
    parcels_gdf = parcels_gdf.to_crs(epsg=4326)

    # מציאת נקודת המרכז של כל חלקה (Centroid)
    # משתמשים ב-to_wkt כדי לוודא שאין שגיאות בפוליגונים ריקים
    centroids = parcels_gdf.geometry.centroid
    parcels_gdf['lon'] = centroids.x
    parcels_gdf['lat'] = centroids.y

    # שומרים רק את העמודות שאנחנו צריכים ומסירים כפילויות
    locations_df = parcels_gdf[['MATCH_ID', 'lat', 'lon']].drop_duplicates(subset=['MATCH_ID'])

    # הצלבה (Merge) בין 20 קבצי המכירות למפת החלקות
    print("\n🔗 Merging sales with precise coordinates...")
    final_df = pd.merge(df_sales, locations_df, left_on='POLYGON_ID', right_on='MATCH_ID', how='left')

    # יצירת הגיאומטריה המוכנה למסד הנתונים (PostGIS)
    mask = final_df['lat'].notna()
    final_df.loc[mask, 'geom'] = "SRID=4326;POINT(" + final_df.loc[mask, 'lon'].astype(str) + " " + final_df.loc[
        mask, 'lat'].astype(str) + ")"

    #  סיכום התוצאות
    found_count = mask.sum()
    missing_count = len(final_df) - found_count
    print(
        f"\n✅ Successfully matched {found_count:,} out of {len(final_df):,} properties ({(found_count / len(final_df)) * 100:.1f}%)!")
    print(f"📌 Missing coordinates: {missing_count:,}")

    # הסרת עמודת העזר והשמירה לקובץ
    final_df = final_df.drop(columns=['MATCH_ID'], errors='ignore')
    final_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"💾 Saved final dataset to {OUTPUT_CSV}")
    print("🚀 You can now copy this CSV to your server and upload it to the database!")

if __name__ == "__main__":
    main()