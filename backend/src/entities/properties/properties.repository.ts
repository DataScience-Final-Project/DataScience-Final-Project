import { Injectable } from "@nestjs/common";
import { QueryTypes } from "sequelize";
import { Sequelize } from "sequelize-typescript";

export type PropertyRow = {
    propertyId: number;
    cityName: string;
    street: string;
    houseNumber: string;
    numRooms: number;
    buildingYear: number;
    propertyType: string;
    floorNumber: number;
    price: number;
};

@Injectable()
export class PropertiesRepository {
    constructor(private readonly sequelize: Sequelize) {}

    fetchByNeighborhood(neighborhoodName: string): Promise<PropertyRow[]> {
        return this.sequelize.query<PropertyRow>(
            `
            SELECT DISTINCT ON (p.property_id)
                p.property_id       AS "propertyId",
                p.city_name         AS "cityName",
                p.street,
                p.house_number      AS "houseNumber",
                p.num_rooms         AS "numRooms",
                p.building_year     AS "buildingYear",
                p.property_type     AS "propertyType",
                p.floor_number      AS "floorNumber",
                t.sale_price        AS "price"
            FROM properties p
            JOIN transactions t ON t.property_id = p.property_id
            WHERE p.geom IS NOT NULL
              AND ST_Within(
                    p.geom,
                    (SELECT geom FROM neighborhood_predictions WHERE neighborhood_name = :neighborhoodName LIMIT 1)
                  )
              AND EXTRACT(YEAR FROM t.sale_date) = (
                    SELECT baseline_year FROM neighborhood_predictions WHERE neighborhood_name = :neighborhoodName LIMIT 1
                  )
            ORDER BY p.property_id, t.sale_price DESC
            `,
            {
                replacements: { neighborhoodName },
                type: QueryTypes.SELECT,
            },
        );
    }
}
