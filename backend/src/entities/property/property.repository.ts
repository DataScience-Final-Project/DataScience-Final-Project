import { Injectable } from '@nestjs/common';
import { QueryTypes } from 'sequelize';
import { Sequelize } from 'sequelize-typescript';

export type PropertyFilters = {
  page?: number;
  pageSize?: number;
  propertyId?: number;
  clusterId?: number;
  search?: string;
  city?: string;
  minRooms?: number;
  maxRooms?: number;
  minBuildingFloors?: number;
  maxBuildingFloors?: number;
  minBuildingYear?: number;
  maxBuildingYear?: number;
  propertyType?: number;
  minPrice?: number;
  maxPrice?: number;
  poiTypeId?: number;
  poiSource?: 'current' | 'future' | 'both';
  poiDistanceMeters?: number;
};

type PropertyRow = {
  propertyId: number;
  cityName: string | null;
  street: string | null;
  houseNumber: string | null;
  lat: number | null;
  lon: number | null;
  locationAccuracy: number | null;
  numRooms: number | null;
  buildingYear: number | null;
  buildingFloors: number | null;
  propertyType: number | null;
  latestSalePrice: number | null;
  latestSaleDate: string | null;
  clusterId: number | null;
  total: string | number;
};

const DEFAULT_PAGE_SIZE = 25;
const MAX_PAGE_SIZE = 100;
const DEFAULT_POI_DISTANCE_METERS = 1_000;

function positiveInteger(value: number | undefined, fallback: number) {
  if (!Number.isFinite(value) || !value || value < 1) return fallback;
  return Math.floor(value);
}

function propertyLocationSql(alias: string) {
  return `COALESCE(
    ${alias}.geom,
    CASE
      WHEN ${alias}.lon IS NOT NULL AND ${alias}.lat IS NOT NULL
      THEN ST_SetSRID(ST_MakePoint(${alias}.lon, ${alias}.lat), 4326)
    END
  )`;
}

@Injectable()
export class PropertyRepository {
  constructor(private readonly sequelize: Sequelize) {}

  async findAll(filters: PropertyFilters) {
    const page = filters.propertyId ? 1 : positiveInteger(filters.page, 1);
    const pageSize = Math.min(positiveInteger(filters.pageSize, DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE);
    const offset = (page - 1) * pageSize;
    const poiSource = filters.poiSource ?? 'both';
    const poiDistanceMeters = positiveInteger(filters.poiDistanceMeters, DEFAULT_POI_DISTANCE_METERS);
    const where: string[] = [];
    const replacements: Record<string, unknown> = {
      limit: pageSize,
      offset,
      poiDistanceMeters,
    };

    if (filters.propertyId) {
      where.push('p.property_id = :propertyId');
      replacements.propertyId = filters.propertyId;
    }
    if (filters.clusterId) {
      where.push('cluster.id = :clusterId');
      replacements.clusterId = filters.clusterId;
    }
    if (filters.city?.trim()) {
      where.push('LOWER(COALESCE(p.city_name, \'\')) = LOWER(:city)');
      replacements.city = filters.city.trim();
    }
    if (filters.minRooms !== undefined) {
      where.push('p.num_rooms >= :minRooms');
      replacements.minRooms = filters.minRooms;
    }
    if (filters.maxRooms !== undefined) {
      where.push('p.num_rooms <= :maxRooms');
      replacements.maxRooms = filters.maxRooms;
    }
    if (filters.minBuildingFloors !== undefined) {
      where.push('p.building_floors >= :minBuildingFloors');
      replacements.minBuildingFloors = filters.minBuildingFloors;
    }
    if (filters.maxBuildingFloors !== undefined) {
      where.push('p.building_floors <= :maxBuildingFloors');
      replacements.maxBuildingFloors = filters.maxBuildingFloors;
    }
    if (filters.minBuildingYear !== undefined) {
      where.push('p.building_year >= :minBuildingYear');
      replacements.minBuildingYear = filters.minBuildingYear;
    }
    if (filters.maxBuildingYear !== undefined) {
      where.push('p.building_year <= :maxBuildingYear');
      replacements.maxBuildingYear = filters.maxBuildingYear;
    }
    if (filters.propertyType !== undefined) {
      where.push('p.property_type = :propertyType');
      replacements.propertyType = filters.propertyType;
    }
    if (filters.minPrice !== undefined) {
      where.push('latest_transaction.sale_price >= :minPrice');
      replacements.minPrice = filters.minPrice;
    }
    if (filters.maxPrice !== undefined) {
      where.push('latest_transaction.sale_price <= :maxPrice');
      replacements.maxPrice = filters.maxPrice;
    }
    if (filters.search?.trim()) {
      where.push(`(
        CAST(p.property_id AS text) ILIKE :search
        OR COALESCE(p.city_name, '') ILIKE :search
        OR COALESCE(p.street, '') ILIKE :search
        OR COALESCE(p.house_number, '') ILIKE :search
        OR COALESCE(p.num_rooms::text, '') ILIKE :search
        OR COALESCE(p.building_year::text, '') ILIKE :search
        OR COALESCE(p.building_floors::text, '') ILIKE :search
        OR COALESCE(p.property_type::text, '') ILIKE :search
        OR COALESCE(latest_transaction.sale_price::text, '') ILIKE :search
        OR COALESCE(features.feature_data::text, '') ILIKE :search
      )`);
      replacements.search = `%${filters.search.trim()}%`;
    }
    if (filters.poiTypeId !== undefined) {
      replacements.poiTypeId = filters.poiTypeId;
      const currentClause = poiSource !== 'future'
        ? `EXISTS (
            SELECT 1
            FROM poi_current poi
            WHERE poi.poi_type_id = :poiTypeId
              AND poi.geom IS NOT NULL
              AND p.location_geom IS NOT NULL
              AND ST_DWithin(p.location_geom::geography, poi.geom::geography, :poiDistanceMeters)
          )`
        : 'FALSE';
      const futureClause = poiSource !== 'current'
        ? `EXISTS (
            SELECT 1
            FROM poi_future poi
            WHERE poi.poi_type_id = :poiTypeId
              AND poi.geom IS NOT NULL
              AND p.location_geom IS NOT NULL
              AND ST_DWithin(p.location_geom::geography, poi.geom::geography, :poiDistanceMeters)
          )`
        : 'FALSE';
      where.push(`(${currentClause} OR ${futureClause})`);
    }

    const rows = await this.sequelize.query<PropertyRow>(
      `
        WITH properties_with_location AS (
          SELECT p.*, ${propertyLocationSql('p')} AS location_geom
          FROM properties p
        )
        SELECT
          p.property_id AS "propertyId",
          p.city_name AS "cityName",
          p.street,
          p.house_number AS "houseNumber",
          p.lat,
          p.lon,
          p.location_accuracy AS "locationAccuracy",
          p.num_rooms AS "numRooms",
          p.building_year AS "buildingYear",
          p.building_floors AS "buildingFloors",
          p.property_type AS "propertyType",
          latest_transaction.sale_price AS "latestSalePrice",
          latest_transaction.sale_date AS "latestSaleDate",
          cluster.id AS "clusterId",
          COUNT(*) OVER() AS total
        FROM properties_with_location p
        LEFT JOIN LATERAL (
          SELECT t.sale_price, t.sale_date
          FROM transactions t
          WHERE t.property_id = p.property_id
          ORDER BY t.sale_date DESC NULLS LAST, t.transaction_id DESC
          LIMIT 1
        ) latest_transaction ON TRUE
        LEFT JOIN LATERAL (
          SELECT pfs.snapshot_year, pfs.horizon_years, to_jsonb(pfs) AS feature_data
          FROM property_features_snapshot pfs
          WHERE pfs.property_id = p.property_id
          ORDER BY pfs.snapshot_year DESC NULLS LAST, pfs.horizon_years DESC NULLS LAST
          LIMIT 1
        ) features ON TRUE
        LEFT JOIN LATERAL (
          SELECT g.id
          FROM growth_clusters g
          WHERE p.location_geom IS NOT NULL AND ST_Intersects(g.geom, p.location_geom)
          ORDER BY g.id
          LIMIT 1
        ) cluster ON TRUE
        ${where.length ? `WHERE ${where.join('\n AND ')}` : ''}
        ORDER BY p.property_id DESC
        LIMIT :limit OFFSET :offset
      `,
      { replacements, type: QueryTypes.SELECT },
    );

    return {
      items: rows.map(({ total: _total, ...property }) => property),
      total: rows.length ? Number(rows[0].total) : 0,
      page,
      pageSize,
    };
  }

  async findFilterOptions() {
    const [cities, propertyTypes, poiTypes] = await Promise.all([
      this.sequelize.query<{ cityName: string }>(
        `SELECT DISTINCT city_name AS "cityName"
         FROM properties
         WHERE city_name IS NOT NULL AND btrim(city_name) <> ''
         ORDER BY city_name`,
        { type: QueryTypes.SELECT },
      ),
      this.sequelize.query<{ propertyType: number }>(
        `SELECT DISTINCT property_type AS "propertyType"
         FROM properties
         WHERE property_type IS NOT NULL
         ORDER BY property_type`,
        { type: QueryTypes.SELECT },
      ),
      this.sequelize.query<{ id: number; name: string }>(
        `SELECT
           poi_type_id AS id,
           COALESCE(
             to_jsonb(poi_types)->>'name',
             to_jsonb(poi_types)->>'poi_type_name',
             'POI type ' || poi_type_id::text
           ) AS name
         FROM poi_types
         ORDER BY name, id`,
        { type: QueryTypes.SELECT },
      ),
    ]);

    return { cities, propertyTypes, poiTypes };
  }

  async findOne(propertyId: number) {
    const [property] = await this.sequelize.query<Record<string, unknown>>(
      `
        WITH property_with_location AS (
          SELECT p.*, ${propertyLocationSql('p')} AS location_geom
          FROM properties p
          WHERE p.property_id = :propertyId
        )
        SELECT
          p.property_id AS "propertyId",
          p.city_name AS "cityName",
          p.street,
          p.house_number AS "houseNumber",
          p.lat,
          p.lon,
          p.location_accuracy AS "locationAccuracy",
          p.num_rooms AS "numRooms",
          p.building_year AS "buildingYear",
          p.building_floors AS "buildingFloors",
          p.property_type AS "propertyType",
          latest_transaction.sale_price AS "latestSalePrice",
          latest_transaction.sale_date AS "latestSaleDate",
          cluster.id AS "clusterId",
          features.snapshot_year AS "featuresSnapshotYear",
          features.horizon_years AS "featuresHorizonYears",
          features.feature_data AS features,
          COALESCE(nearby_pois.items, '[]'::json) AS "nearbyPois"
        FROM property_with_location p
        LEFT JOIN LATERAL (
          SELECT t.sale_price, t.sale_date
          FROM transactions t
          WHERE t.property_id = p.property_id
          ORDER BY t.sale_date DESC NULLS LAST, t.transaction_id DESC
          LIMIT 1
        ) latest_transaction ON TRUE
        LEFT JOIN LATERAL (
          SELECT pfs.snapshot_year, pfs.horizon_years, to_jsonb(pfs) - 'property_id' AS feature_data
          FROM property_features_snapshot pfs
          WHERE pfs.property_id = p.property_id
          ORDER BY pfs.snapshot_year DESC NULLS LAST, pfs.horizon_years DESC NULLS LAST
          LIMIT 1
        ) features ON TRUE
        LEFT JOIN LATERAL (
          SELECT g.id
          FROM growth_clusters g
          WHERE p.location_geom IS NOT NULL AND ST_Intersects(g.geom, p.location_geom)
          ORDER BY g.id
          LIMIT 1
        ) cluster ON TRUE
        LEFT JOIN LATERAL (
          SELECT json_agg(poi ORDER BY (poi->>'distanceMeters')::numeric) AS items
          FROM (
            SELECT poi
            FROM (
              SELECT json_build_object(
                'source', 'current',
                'typeId', current_poi.poi_type_id,
                'typeName', COALESCE(
                  to_jsonb(current_type)->>'name',
                  to_jsonb(current_type)->>'poi_type_name',
                  'POI type ' || current_poi.poi_type_id::text
                ),
                'distanceMeters', ROUND(ST_Distance(p.location_geom::geography, current_poi.geom::geography)::numeric, 0)
              ) AS poi
              FROM poi_current current_poi
              LEFT JOIN poi_types current_type ON current_type.poi_type_id = current_poi.poi_type_id
              WHERE p.location_geom IS NOT NULL
                AND current_poi.geom IS NOT NULL
                AND ST_DWithin(p.location_geom::geography, current_poi.geom::geography, 10000)
              UNION ALL
              SELECT json_build_object(
                'source', 'future',
                'typeId', future_poi.poi_type_id,
                'typeName', COALESCE(
                  to_jsonb(future_type)->>'name',
                  to_jsonb(future_type)->>'poi_type_name',
                  'POI type ' || future_poi.poi_type_id::text
                ),
                'plannedYear', future_poi.planned_year,
                'distanceMeters', ROUND(ST_Distance(p.location_geom::geography, future_poi.geom::geography)::numeric, 0)
              ) AS poi
              FROM poi_future future_poi
              LEFT JOIN poi_types future_type ON future_type.poi_type_id = future_poi.poi_type_id
              WHERE p.location_geom IS NOT NULL
                AND future_poi.geom IS NOT NULL
                AND ST_DWithin(p.location_geom::geography, future_poi.geom::geography, 10000)
            ) poi_rows
            ORDER BY (poi->>'distanceMeters')::numeric
            LIMIT 50
          ) closest_pois
        ) nearby_pois ON TRUE
      `,
      { replacements: { propertyId }, type: QueryTypes.SELECT },
    );

    return property ?? null;
  }
}
