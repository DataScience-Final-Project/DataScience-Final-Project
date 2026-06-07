import { Column, DataType, Model, Table } from "sequelize-typescript";

@Table({ tableName: 'neighborhood_predictions', timestamps: false })
export class NeighborhoodPrediction extends Model<NeighborhoodPrediction> {
    @Column({ type: DataType.STRING, field: 'city_name' })
    declare cityName: string;

    @Column({ type: DataType.STRING, field: 'neighborhood_name' })
    declare neighborhoodName: string;

    @Column({ type: DataType.INTEGER, field: 'baseline_year' })
    declare baselineYear: number;

    @Column({ type: DataType.INTEGER, field: 'price_now' })
    declare priceNow: number;

    @Column({ type: DataType.FLOAT, field: 'growth_5y_pct' })
    declare growth5y: number;

    @Column({ type: DataType.FLOAT, field: 'growth_10y_pct' })
    declare growth10y: number;

    @Column({ type: DataType.GEOMETRY })
    declare geom: unknown;
}
