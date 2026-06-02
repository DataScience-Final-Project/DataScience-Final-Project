import { Injectable } from "@nestjs/common";
import { InjectModel } from "@nestjs/sequelize";
import { QueryTypes } from "sequelize";
import { Sequelize } from "sequelize-typescript";
import cities from "../israel_cities_names_and__geometric_data.json";
import { GrowthCluster } from "./growthCluster.model";

type PolygonGeometry = {
    type: 'Polygon';
    coordinates: number[][][];
};

type CityCenter = {
    name: string;
    long: number;
    latt: number;
};

const CITY_CENTER_MAX_DISTANCE_METERS = 30_000;
const cityCenters = JSON.stringify(
    (cities as CityCenter[]).map(city => ({
        name: city.name.trim(),
        long: city.long,
        latt: city.latt,
    })),
);

export type GrowthClusterRow = {
    id: number;
    clusterId: number;
    avgGrowth: number;
    certainty: number;
    geom: PolygonGeometry | string;
    cities: string[];
    createdAt: Date;
};

@Injectable()
export class GrowthClusterRepository {
    constructor(
        @InjectModel(GrowthCluster) private readonly growthClusterModel: typeof GrowthCluster,
        private readonly sequelize: Sequelize,
    ) { }

    fetchAll(city?: string): Promise<GrowthClusterRow[]> {
        const normalizedCity = city?.trim() || null;

        return this.sequelize.query<GrowthClusterRow>(
            `
            WITH city_centers AS (
                SELECT
                    btrim(name) AS name,
                    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography AS geom
                FROM jsonb_to_recordset(CAST(:cityCenters AS jsonb))
                    AS city_center(name text, longitude double precision, latitude double precision)
            )
            SELECT
                g.id,
                g.cluster_id AS "clusterId",
                g.avg_growth AS "avgGrowth",
                g.certainty,
                ST_AsGeoJSON(g.geom)::json AS geom,
                COALESCE(c.cities, ARRAY[]::text[]) AS cities,
                g.created_at AS "createdAt"
            FROM growth_clusters g
            LEFT JOIN LATERAL (
                SELECT array_agg(DISTINCT btrim(p.city_name) ORDER BY btrim(p.city_name)) AS cities
                FROM properties p
                INNER JOIN city_centers cc ON cc.name = btrim(p.city_name)
                WHERE p.geom IS NOT NULL
                    AND p.city_name IS NOT NULL
                    AND btrim(p.city_name) <> ''
                    AND (:city IS NULL OR btrim(p.city_name) = :city)
                    AND ST_DWithin(p.geom::geography, cc.geom, :cityCenterMaxDistanceMeters)
                    AND ST_Intersects(g.geom, p.geom)
            ) c ON TRUE
            WHERE (:city IS NULL OR c.cities IS NOT NULL)
            ORDER BY g.id
            `,
            {
                replacements: {
                    city: normalizedCity,
                    cityCenters,
                    cityCenterMaxDistanceMeters: CITY_CENTER_MAX_DISTANCE_METERS,
                },
                type: QueryTypes.SELECT,
            },
        );
    }
}
