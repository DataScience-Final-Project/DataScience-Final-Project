import { Body, Controller, Get, Param, Post, Query } from "@nestjs/common";
import { HeatmapService, HeatmapFiltersDto } from "./heatmap.service";

@Controller('heatmap')
export class HeatmapController {
    constructor(private readonly service: HeatmapService) { }

    @Get('poi-types')
    getPoiTypes() {
        return this.service.getPoiTypes();
    }

    @Post('')
    getHeatmap(@Body() filters: HeatmapFiltersDto) {
        return this.service.getHeatmap(filters);
    }

    @Post(':hexId/properties')
    getHexProperties(@Param('hexId') hexId: string, @Body() body: { years?: number } & Partial<HeatmapFiltersDto>) {
        return this.service.getHexProperties(hexId, Number(body.years) || 5, body);
    }
}
