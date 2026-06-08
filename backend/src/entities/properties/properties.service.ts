import { Injectable } from "@nestjs/common";
import { PropertiesRepository } from "./properties.repository";

@Injectable()
export class PropertiesService {
    constructor(private readonly repository: PropertiesRepository) {}

    fetchByNeighborhood(neighborhoodName: string) {
        return this.repository.fetchByNeighborhood(neighborhoodName);
    }
}
