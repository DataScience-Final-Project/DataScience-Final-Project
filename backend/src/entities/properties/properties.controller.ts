import { Controller, Get, Query } from "@nestjs/common";
import { PropertiesService } from "./properties.service";

@Controller('properties-in-area')
export class PropertiesController {
    constructor(private readonly service: PropertiesService) {}

    @Get('')
    fetchByNeighborhood(@Query('neighborhoodName') neighborhoodName: string) {
        return this.service.fetchByNeighborhood(neighborhoodName);
    }
}
