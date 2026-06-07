import { Controller, Get, Query } from "@nestjs/common";
import { NeighborhoodPredictionService } from "./neighborhoodPrediction.service";

@Controller('neighborhood-predictions')
export class NeighborhoodPredictionController {
    constructor(private readonly service: NeighborhoodPredictionService) { }

    @Get('')
    fetchAll(@Query('years') years: number, @Query('city') city?: string) {
        return this.service.fetchAll(years, city);
    }
}
