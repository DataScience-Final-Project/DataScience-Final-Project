import { Module } from "@nestjs/common";
import { PropertiesController } from "./properties.controller";
import { PropertiesService } from "./properties.service";
import { PropertiesRepository } from "./properties.repository";

@Module({
    controllers: [PropertiesController],
    providers: [PropertiesService, PropertiesRepository],
})
export class PropertiesModule {}
