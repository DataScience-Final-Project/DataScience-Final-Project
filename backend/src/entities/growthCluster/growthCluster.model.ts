import { Column, DataType, Model, PrimaryKey, Table } from "sequelize-typescript";

export type IGrowthCluster = {
    id: number;
    clusterId: number;
    avgGrowth: number;
    certainty: number;
    geom: string;
    createdAt: Date;
}

type PolygonGeometry = {
  type: 'Polygon';
  coordinates: number[][][];
};

@Table({ tableName: 'growth_clusters', timestamps: false })
export class GrowthCluster extends Model<GrowthCluster> {
    @PrimaryKey
    @Column({ type: DataType.INTEGER, autoIncrement: true })
    declare id: number;

    @Column({ type: DataType.INTEGER, field: 'cluster_id' })
    declare clusterId: number;

    @Column({ type: DataType.REAL, field: 'avg_growth' })
    declare avgGrowth: number;

    @Column({ type: DataType.REAL })
    declare certainty: number;

    @Column({ type: DataType.GEOMETRY })
    declare geom: PolygonGeometry;

    @Column({ type: DataType.DATE, field: 'created_at' })
    declare createdAt: Date;
}