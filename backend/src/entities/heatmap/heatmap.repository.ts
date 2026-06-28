import { Injectable } from "@nestjs/common";
import { QueryTypes } from "sequelize";
import { Sequelize } from "sequelize-typescript";

export type PropertyPredictionRow = {
    propertyId: number;
    lat: number;
    lon: number;
    cityName: string;
    street: string;
    houseNumber: string;
    numRooms: number;
    buildingYear: number;
    buildingFloors: number;
    propertyType: number;
    logChange: number;
    percentChange: number;
    price: number;
};

export type HexPropertyRow = {
    propertyId: number;
    cityName: string;
    street: string;
    houseNumber: string;
    numRooms: number;
    buildingYear: number;
    buildingFloors: number;
    propertyType: string;
    percentChange: number;
    price: number;
};

export type HeatmapFilters = {
    horizonYears: 5 | 10;
    city?: string | null;
    minPrice?: number | null;
    maxPrice?: number | null;
    minRooms?: number | null;
    maxRooms?: number | null;
    propertyType?: number | null;
};

@Injectable()
export class HeatmapRepository {
    constructor(private readonly sequelize: Sequelize) { }

    fetchFiltered(filters: HeatmapFilters): Promise<PropertyPredictionRow[]> {
        return this.sequelize.query<PropertyPredictionRow>(
            `
            SELECT
                p.property_id         AS "propertyId",
                p.lat,
                p.lon,
                p.city_name           AS "cityName",
                p.street,
                p.house_number        AS "houseNumber",
                p.num_rooms           AS "numRooms",
                p.building_year       AS "buildingYear",
                p.building_floors     AS "buildingFloors",
                p.property_type       AS "propertyType",
                pp.log_change         AS "logChange",
                pp.percent_change     AS "percentChange",
                pp.price_at_snapshot  AS "price"
            FROM properties p
            JOIN property_predictions pp
                ON pp.property_id = p.property_id
               AND pp.horizon_years = :horizonYears
            WHERE p.lat IS NOT NULL
              AND p.lon IS NOT NULL
              AND (:city::text          IS NULL OR p.city_name             = :city)
              AND (:minRooms::float     IS NULL OR p.num_rooms            >= :minRooms)
              AND (:maxRooms::float     IS NULL OR p.num_rooms            <= :maxRooms)
              AND (:propertyType::smallint IS NULL OR p.property_type     = :propertyType)
              AND (:minPrice::bigint    IS NULL OR pp.price_at_snapshot   >= :minPrice)
              AND (:maxPrice::bigint    IS NULL OR pp.price_at_snapshot   <= :maxPrice)
            `,
            {
                replacements: {
                    horizonYears: filters.horizonYears,
                    city:         filters.city         ?? null,
                    minPrice:     filters.minPrice     ?? null,
                    maxPrice:     filters.maxPrice     ?? null,
                    minRooms:     filters.minRooms     ?? null,
                    maxRooms:     filters.maxRooms     ?? null,
                    propertyType: filters.propertyType ?? null,
                },
                type: QueryTypes.SELECT,
            },
        );
    }

    fetchByHex(hexPolygonWkt: string, horizonYears: 5 | 10): Promise<HexPropertyRow[]> {
        return this.sequelize.query<HexPropertyRow>(
            `
            SELECT DISTINCT ON (p.property_id)
                p.property_id         AS "propertyId",
                p.city_name           AS "cityName",
                p.street,
                p.house_number        AS "houseNumber",
                p.num_rooms           AS "numRooms",
                p.building_year       AS "buildingYear",
                p.building_floors     AS "buildingFloors",
                p.property_type       AS "propertyType",
                pp.percent_change     AS "percentChange",
                pp.price_at_snapshot  AS "price"
            FROM properties p
            JOIN property_predictions pp
                ON pp.property_id = p.property_id
               AND pp.horizon_years = :horizonYears
            WHERE p.geom IS NOT NULL
              AND ST_Within(p.geom, ST_GeomFromText(:wkt, 4326))
            ORDER BY p.property_id
            `,
            {
                replacements: { wkt: hexPolygonWkt, horizonYears },
                type: QueryTypes.SELECT,
            },
        );
    }
}