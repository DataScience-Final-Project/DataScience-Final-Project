import { Injectable } from "@nestjs/common";
import { InjectModel } from "@nestjs/sequelize";
import { QueryTypes } from "sequelize";
import { Sequelize } from "sequelize-typescript";
import { GrowthCluster } from "./growthCluster.model";

type PolygonGeometry = {
    type: 'Polygon';
    coordinates: number[][][];
};

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
                SELECT array_agg(DISTINCT p.city_name ORDER BY p.city_name) AS cities
                FROM properties p
                WHERE p.geom IS NOT NULL
                    AND p.city_name IS NOT NULL
                    AND ST_Intersects(g.geom, p.geom)
            ) c ON TRUE
            WHERE (:city IS NULL OR :city = ANY(c.cities))
            ORDER BY g.id
            `,
            {
                replacements: { city: normalizedCity },
                type: QueryTypes.SELECT,
            },
        );
    }
}
