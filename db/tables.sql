CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE properties (
  property_id      BIGSERIAL PRIMARY KEY,
  city_name        TEXT,
  street           TEXT,
  house_number     TEXT,

  lat              DOUBLE PRECISION,
  lon              DOUBLE PRECISION,
  geom             GEOMETRY(Point, 4326),
  location_accuracy SMALLINT,

  num_rooms        FLOAT,
  building_year    INT,
  building_floors  INT,
  property_type    SMALLINT
);

CREATE INDEX idx_properties_geom
ON properties
USING GIST (geom);

CREATE TABLE transactions (
  transaction_id  BIGSERIAL PRIMARY KEY,
  property_id     BIGINT REFERENCES properties(property_id),
  sale_date       DATE,
  sale_price      BIGINT
);

CREATE INDEX idx_transactions_property
ON transactions(property_id);

CREATE INDEX idx_transactions_date
ON transactions(sale_date);

CREATE TABLE poi_types (
  poi_type_id  SMALLINT PRIMARY KEY,
  name         TEXT UNIQUE
);

CREATE TABLE poi_current (
  poi_id       BIGSERIAL PRIMARY KEY,
  poi_type_id  SMALLINT REFERENCES poi_types(poi_type_id),
  geom         GEOMETRY(Point, 4326)
);

CREATE INDEX idx_poi_current_geom
ON poi_current
USING GIST (geom);

CREATE TABLE poi_future (
  poi_id        BIGSERIAL PRIMARY KEY,
  poi_type_id   SMALLINT REFERENCES poi_types(poi_type_id),
  geom          GEOMETRY(Point, 4326),
  planned_year  INT
);

CREATE INDEX idx_poi_future_geom
ON poi_future
USING GIST (geom);

CREATE TABLE price_labels (
  property_id        BIGINT,
  snapshot_year      INT,
  horizon_years      SMALLINT,

  price_at_snapshot  BIGINT,
  price_after_horizon BIGINT,
  log_return         FLOAT,

  PRIMARY KEY (property_id, snapshot_year, horizon_years)
);

CREATE TABLE property_features_snapshot (

  -- ================================
  -- ========== IDENTIFIERS ==========
  -- ================================
  property_id          BIGINT,
  snapshot_year        INT,
  horizon_years        SMALLINT,   -- 5 / 7 / 10


  -- ==========================================
  -- ========== STATIC PROPERTY FEATURES =======
  -- ==========================================
  num_rooms            FLOAT,
  building_year        INT,
  building_floors      INT,
  property_type        SMALLINT,


  -- =================================================
  -- ========== CURRENT POIs (BASELINE VALUE) =========
  -- =================================================
  -- מצב קיים של הסביבה בזמן snapshot_year


  -- ---------- EDUCATION ----------
  num_schools_1km              INT,
  num_schools_2km              INT,
  min_dist_school              FLOAT,

  num_kindergartens_1km        INT,


  -- ---------- TRANSPORT (EXISTING) ----------
  min_dist_train_station       FLOAT,
  num_train_stations_1km       INT,
  num_train_stations_3km       INT,

  min_dist_light_rail          FLOAT,
  num_light_rail_stops_1km     INT,

  num_bus_stops_500m           INT,
  num_bus_stops_1km            INT,


  -- ---------- HEALTH ----------
  min_dist_hospital            FLOAT,
  num_hospitals_3km            INT,
  num_clinics_1km              INT,


  -- ---------- GREEN & QUALITY OF LIFE ----------
  min_dist_large_park          FLOAT,
  num_parks_500m               INT,
  num_parks_1km                INT,


  -- ---------- COMMERCIAL / DAILY NEEDS ----------
  num_supermarkets_500m        INT,
  num_supermarkets_1km         INT,
  num_malls_2km                INT,
  num_malls_5km                INT,

  -- ---------- EMPLOYMENT / ACTIVITY ----------
  num_offices_2km              INT,
  num_offices_5km              INT,
  num_hotels_2km               INT,
  num_hotels_5km               INT,

  -- =================================================
  -- ========== FUTURE POIs (UPSIDE / CATALYST) =======
  -- =================================================
  -- תשתיות חדשות שצפויות להיבנות עד snapshot_year + horizon_years


  -- ---------- FUTURE TRANSPORT (CRITICAL) ----------
  min_dist_future_train        FLOAT,
  num_future_train_1km         INT,
  num_future_train_3km         INT,
  num_future_train_5km         INT,
  num_future_train_10km         INT,

  -- ⭐ Smooth / Accessibility score
  future_train_access_score_10km FLOAT,


  min_dist_future_light_rail   FLOAT,
  num_future_light_rail_1km    INT,
  num_future_light_rail_3km    INT,

  future_light_rail_access_score_10km FLOAT,


  -- ---------- FUTURE ROADS / INTERCHANGES ----------
  min_dist_future_road         FLOAT,
  num_future_roads_2km         INT,


  -- ---------- FUTURE EDUCATION ----------
  num_future_schools_1km       INT,
  num_future_schools_2km       INT,
  num_future_schools_5km       INT,

  -- ---------- FUTURE COMMERCIAL ----------
  num_future_malls_2km         INT,
  num_future_malls_5km         INT,


  -- ==========================================
  -- ========== META (NOT FOR ML) ===============
  -- ==========================================
  distance_method      SMALLINT,   -- 1=property distance, 2=coarse/fallback
  features_updated_at  TIMESTAMP,


  PRIMARY KEY (property_id, snapshot_year, horizon_years)
);
