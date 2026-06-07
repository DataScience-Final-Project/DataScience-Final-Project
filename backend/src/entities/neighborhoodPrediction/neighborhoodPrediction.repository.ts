import { Injectable } from "@nestjs/common";
import { QueryTypes } from "sequelize";
import { Sequelize } from "sequelize-typescript";

export type NeighborhoodPredictionRow = {
    cityName: string;
    neighborhoodName: string;
    grade: number;
    horizonYears: number;
    priceNow: number;
    geom: object;
};

@Injectable()
export class NeighborhoodPredictionRepository {
    constructor(private readonly sequelize: Sequelize) { }

    fetchAll(horizonYears: 5 | 10, city?: string): Promise<NeighborhoodPredictionRow[]> {
        return this.sequelize.query<NeighborhoodPredictionRow>(
            `
            SELECT
                city_name AS "cityName",
                neighborhood_name AS "neighborhoodName",
                CASE WHEN :horizonYears = 10 THEN growth_10y_pct ELSE growth_5y_pct END AS grade,
                :horizonYears AS "horizonYears",
                price_now AS "priceNow",
                ST_AsGeoJSON(geom)::json AS geom
            FROM neighborhood_predictions
            WHERE (:city::text IS NULL OR city_name = :city)
            ORDER BY city_name, neighborhood_name
            `,
            {
                replacements: { horizonYears, city: city ?? null },
                type: QueryTypes.SELECT,
            },
        );
    }
}