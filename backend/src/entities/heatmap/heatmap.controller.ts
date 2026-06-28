import { Body, Controller, Get, Param, Post, Query } from "@nestjs/common";
import { HeatmapService, HeatmapFiltersDto } from "./heatmap.service";

@Controller('heatmap')
export class HeatmapController {
    constructor(private readonly service: HeatmapService) { }

    @Post('')
    getHeatmap(@Body() filters: HeatmapFiltersDto) {
        return this.service.getHeatmap(filters);
    }

    @Get(':hexId/properties')
    getHexProperties(@Param('hexId') hexId: string, @Query('years') years: string) {
        return this.service.getHexProperties(hexId, Number(years) || 5);
    }
}
