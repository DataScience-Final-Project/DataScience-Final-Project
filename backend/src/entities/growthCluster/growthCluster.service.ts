import { Injectable } from "@nestjs/common";
import { GrowthClusterRepository } from "./growthCluster.repository";

@Injectable()
export class GrowthClusterService {
    constructor(private readonly repository: GrowthClusterRepository) { }

    async fetchAll(years: number, city?: string) {
        const growthClusters = await this.repository.fetchAll(city);

        const yearsAhead = Number.isFinite(Number(years)) ? Number(years) : 0;

        return growthClusters.map(cluster => {
            const geom = typeof cluster.geom === 'string' ? JSON.parse(cluster.geom) : cluster.geom;
            const polygonGrowthPercent =
                (Math.pow(1 + cluster.avgGrowth, yearsAhead) - 1) * 100;

            return {
                grade: Number(polygonGrowthPercent.toFixed(3)),
                cities: cluster.cities,
                coordinates: geom.coordinates[0].map((coord: number[]) => ({ x: coord[0], y: coord[1] }))
            };
        });
    }
}
