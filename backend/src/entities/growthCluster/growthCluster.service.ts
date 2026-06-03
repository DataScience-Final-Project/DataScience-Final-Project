import { Injectable } from "@nestjs/common";
import { GrowthClusterRepository } from "./growthCluster.repository";

/** DB may store 0.08 (rate) or 8 (percent) — always return decimal rate for compounding. */
function toDecimalGrowthRate(avgGrowth: number): number {
    if (!Number.isFinite(avgGrowth)) return 0;
    return Math.abs(avgGrowth) > 1 ? avgGrowth / 100 : avgGrowth;
}

@Injectable()
export class GrowthClusterService {
    constructor(private readonly repository: GrowthClusterRepository) { }

    async fetchAll(years: number, city?: string) {
        const growthClusters = await this.repository.fetchAll(city);

        const yearsAhead = Number.isFinite(Number(years)) && Number(years) > 0
            ? Number(years)
            : 1;

        return growthClusters.map(cluster => {
            const geom = typeof cluster.geom === 'string' ? JSON.parse(cluster.geom) : cluster.geom;
            const rate = toDecimalGrowthRate(cluster.avgGrowth);
            const polygonGrowthPercent = (Math.pow(1 + rate, yearsAhead) - 1) * 100;

            return {
                grade: Number(polygonGrowthPercent.toFixed(3)),
                cities: cluster.cities,
                coordinates: geom.coordinates[0].map((coord: number[]) => ({ x: coord[0], y: coord[1] }))
            };
        });
    }
}
