import { Module } from "@nestjs/common";
import { SequelizeModule } from "@nestjs/sequelize";
import { GrowthCluster } from "./growthCluster.model";
import { GrowthClusterController } from "./growthCluster.controller";
import { GrowthClusterRepository } from "./growthCluster.repository";
import { GrowthClusterService } from "./growthCluster.service";

@Module({
    imports: [
        SequelizeModule.forFeature([GrowthCluster]),
    ],
    controllers: [GrowthClusterController],
    providers: [GrowthClusterRepository, GrowthClusterService],
})
export class GrowthClusterModule { }
