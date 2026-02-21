# DataScience-Final-Project

Setup on a New Machine (Windows)
Prerequisites

Git

PostgreSQL + PostGIS (or access to an existing Postgres server)

Miniconda (recommended) or Anaconda

Internet access (only needed for optional Nominatim fallback geocoding)

1) Clone the repository
git clone <YOUR_REPO_URL>
cd DataScience-Final-Project\python_service
2) Create the Conda environment

We use Conda because geo packages (pyrosm/geopandas/shapely/pyproj) are much more reliable on Windows via conda-forge.

2.1 If Conda asks you to accept Terms of Service (ToS)

Run once:

conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/msys2
2.2 Create the environment from environment.yml
conda env create -f environment.yml
conda activate geo

If the env already exists and you want to sync it:

conda env update -f environment.yml --prune
conda activate geo
2.3 Quick sanity check (imports)
python -c "import pyrosm, geopandas, shapely, pyproj, pandas, openpyxl, requests; print('ALL OK')"
3) Create .env for DB credentials

We do NOT commit .env. Use the template.

Copy:

copy .env.example .env

Edit .env with your actual DB connection info:

PGHOST=127.0.0.1
PGPORT=5432
PGDATABASE=your_db
PGUSER=your_user
PGPASSWORD=your_password
4) Put the data files in the correct folders

Raw data is NOT committed to git. Put it locally in the same relative paths.

4.1 OSM PBF (required for address index + POIs)

Place your PBF here:

python_service/data/raw/osm/israel-and-palestine-251213.osm.pbf
4.2 Sales XLSX files (20 cities)

Place all XLSX files here:

python_service/data/raw/sales/cities_xlsx/*.xlsx
4.3 POIs CSV (if you already generated it on another machine)

If you already have the processed POIs CSV:

python_service/data/processed/pois_for_db.csv
5) DB preparation (run once in pgAdmin / psql)
5.1 POI types (minimal)
INSERT INTO poi_types (poi_type_id, poi_type_name)
VALUES
  (1,'school'),(2,'kindergarten'),(3,'train_station'),(4,'light_rail_stop'),
  (5,'bus_stop'),(6,'health_all'),(8,'park'),(9,'supermarket'),
  (10,'mall'),(11,'commercial'),(12,'hotel')
ON CONFLICT (poi_type_id) DO UPDATE
SET poi_type_name = EXCLUDED.poi_type_name;
5.2 Geocoding tables (used for properties geom)
CREATE TABLE IF NOT EXISTS osm_address_index (
  city_name TEXT NOT NULL,
  street TEXT NOT NULL,
  house_number TEXT NOT NULL,
  geom GEOMETRY(Point, 4326),
  PRIMARY KEY (city_name, street, house_number)
);

CREATE TABLE IF NOT EXISTS property_geocode_cache (
  city_name TEXT NOT NULL,
  street TEXT NOT NULL,
  house_number TEXT NOT NULL,
  lat DOUBLE PRECISION,
  lon DOUBLE PRECISION,
  geom GEOMETRY(Point, 4326),
  source TEXT,
  updated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (city_name, street, house_number)
);
6) Run pipelines
6.1 Build property geoms (OSM first, then Nominatim fallback for missing)

From python_service/:

conda activate geo
python -m etl.build_property_geoms
6.2 Upload POIs to Postgres

(Requires data/processed/pois_for_db.csv)

conda activate geo
python -m etl.upload_pois
6.3 Upload sales (properties + transactions)
conda activate geo
python -m etl.upload_sales
Troubleshooting
Conda not recognized

Open Anaconda Prompt / Miniconda Prompt instead of regular PowerShell.

ModuleNotFoundError: No module named 'etl'

Make sure you run from inside python_service/ and run as a module:

cd ...\python_service
python -m etl.upload_pois
Excel read error: No module named openpyxl

Inside env:

pip install openpyxl
Geocoding is slow

The script caches results in property_geocode_cache. Reruns will only process missing rows.
