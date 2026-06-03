import { Controller, Get, Query } from "@nestjs/common";
import { GrowthClusterService } from "./growthCluster.service";

@Controller('growth-clusters')
export class GrowthClusterController {
    constructor(private readonly service: GrowthClusterService) { }

    @Get('')
    fetchAll(@Query('years') years: number, @Query('city') city?: string) {
        return this.service.fetchAll(years, city);
    }
}
