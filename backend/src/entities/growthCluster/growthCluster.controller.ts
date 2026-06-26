import { Controller, Get, Query } from "@nestjs/common";
import { GrowthClusterService } from "./growthCluster.service";

@Controller('growth-clusters')
export class GrowthClusterController {
    constructor(private readonly service: GrowthClusterService) { }

    @Get('')
    fetchAll(
        @Query('years') years: number,
        @Query('city') city?: string,
        @Query('clusterId') clusterId?: number,
    ) {
        return this.service.fetchAll(years, city, clusterId);
    }
}
