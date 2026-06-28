import { Module } from "@nestjs/common";
import { HeatmapController } from "./heatmap.controller";
import { HeatmapService } from "./heatmap.service";
import { HeatmapRepository } from "./heatmap.repository";

@Module({
    controllers: [HeatmapController],
    providers: [HeatmapService, HeatmapRepository],
})
export class HeatmapModule { }