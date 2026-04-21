import { Injectable } from "@nestjs/common";
import { GrowthClusterRepository } from "./growthCluster.repository";

@Injectable()
export class GrowthClusterService {
    constructor(private readonly repository: GrowthClusterRepository) { }

    async fetchAll(years: number) {
        const growthClusters = await this.repository.fetchAll();

        const yearsAhead = Number.isFinite(Number(years)) ? Number(years) : 0;

        return growthClusters.map(cluster => {
            const polygonGrowthPercent =
                (Math.pow(1 + cluster.avgGrowth, yearsAhead) - 1) * 100;

            return {
                grade: Number(polygonGrowthPercent.toFixed(3)),
                coordinates: cluster.geom.coordinates[0].map((coord: number[]) => ({ x: coord[0], y: coord[1] }))
            };
        });
    }
}
