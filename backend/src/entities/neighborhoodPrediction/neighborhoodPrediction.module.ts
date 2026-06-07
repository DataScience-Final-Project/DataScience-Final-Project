import { Module } from "@nestjs/common";
import { NeighborhoodPredictionController } from "./neighborhoodPrediction.controller";
import { NeighborhoodPredictionService } from "./neighborhoodPrediction.service";
import { NeighborhoodPredictionRepository } from "./neighborhoodPrediction.repository";

@Module({
    controllers: [NeighborhoodPredictionController],
    providers: [NeighborhoodPredictionService, NeighborhoodPredictionRepository],
})
export class NeighborhoodPredictionModule { }