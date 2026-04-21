import { Injectable } from "@nestjs/common";
import { InjectModel } from "@nestjs/sequelize";
import { GrowthCluster } from "./growthCluster.model";

@Injectable()
export class GrowthClusterRepository {
    constructor(@InjectModel(GrowthCluster) private readonly growthClusterModel: typeof GrowthCluster) { }

    fetchAll() {
        return this.growthClusterModel.findAll();
    }
}