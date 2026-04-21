import { Controller, Get, Query } from "@nestjs/common";
import { CityService } from "./city.service";

@Controller('cities')
export class CityController {
    constructor(private readonly cityService: CityService) {}

    @Get('')
    fetchAll(@Query('filter') filter: string) {
        return this.cityService.fetchAll(filter);
    }
}