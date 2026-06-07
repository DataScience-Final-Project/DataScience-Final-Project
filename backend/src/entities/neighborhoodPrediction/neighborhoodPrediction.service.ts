import { Injectable } from "@nestjs/common";
import { NeighborhoodPredictionRepository } from "./neighborhoodPrediction.repository";

@Injectable()
export class NeighborhoodPredictionService {
    constructor(private readonly repository: NeighborhoodPredictionRepository) { }

    fetchAll(years: number, city?: string) {
        const horizonYears: 5 | 10 = Number(years) > 5 ? 10 : 5;
        return this.repository.fetchAll(horizonYears, city);
    }
}
