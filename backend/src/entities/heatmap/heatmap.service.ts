import { Injectable } from "@nestjs/common";
import { latLngToCell, cellToBoundary } from "h3-js";
import { HeatmapRepository, HeatmapFilters, PropertyPredictionRow } from "./heatmap.repository";

export class HeatmapFiltersDto {
    years!: number;
    city?: string;
    minPrice?: number;
    maxPrice?: number;
    minRooms?: number;
    maxRooms?: number;
    minFloors?: number;
    maxFloors?: number;
    minGrowth?: number;
    propertyType?: number;
}

const RESOLUTION = 8;

@Injectable()
export class HeatmapService {
    constructor(private readonly repository: HeatmapRepository) { }

    async getHeatmap(dto: HeatmapFiltersDto) {
        const filters: HeatmapFilters = {
            horizonYears: Number(dto.years) > 5 ? 10 : 5,
            city:         dto.city         ?? null,
            minPrice:     dto.minPrice     != null ? Number(dto.minPrice) : null,
            maxPrice:     dto.maxPrice     != null ? Number(dto.maxPrice) : null,
            minRooms:     dto.minRooms     != null ? Number(dto.minRooms) : null,
            maxRooms:     dto.maxRooms     != null ? Number(dto.maxRooms) : null,
            minFloors:    dto.minFloors    != null ? Number(dto.minFloors) : null,
            maxFloors:    dto.maxFloors    != null ? Number(dto.maxFloors) : null,
            minGrowth:    dto.minGrowth    != null ? Number(dto.minGrowth)  : null,
            propertyType: dto.propertyType != null ? Number(dto.propertyType) : null,
        };

        const rows = await this.repository.fetchFiltered(filters);
        return this.aggregateToGeoJSON(rows, filters.horizonYears);
    }

    private aggregateToGeoJSON(rows: PropertyPredictionRow[], horizonYears: 5 | 10) {
        const hexMap = new Map<string, { percentChanges: number[]; properties: PropertyPredictionRow[] }>();

        for (const row of rows) {
            const h3Index = latLngToCell(row.lat, row.lon, RESOLUTION);
            if (!hexMap.has(h3Index)) {
                hexMap.set(h3Index, { percentChanges: [], properties: [] });
            }
            const bucket = hexMap.get(h3Index)!;
            bucket.percentChanges.push(row.percentChange);
            bucket.properties.push(row);
        }

        const features: object[] = [];
        for (const [h3Index, bucket] of hexMap.entries()) {
            const avg =
                bucket.percentChanges.reduce((a, b) => a + b, 0) /
                bucket.percentChanges.length;

            // cellToBoundary returns [lat, lon]; GeoJSON needs [lon, lat]
            const boundary = cellToBoundary(h3Index);
            const ring = boundary.map(([lat, lon]) => [lon, lat]);
            ring.push(ring[0]); // close the GeoJSON ring

            features.push({
                type: "Feature",
                geometry: {
                    type: "Polygon",
                    coordinates: [ring],
                },
                properties: {
                    h3Index,
                    neighborhoodName: `Hex ${h3Index}`,
                    grade: parseFloat(avg.toFixed(2)),
                    horizonYears,
                    count: bucket.properties.length,
                    suggestedAreas: [...new Set(bucket.properties.map(p => p.cityName).filter(Boolean))],
                },
            });
        }

        return { type: "FeatureCollection", features };
    }

    async getHexProperties(hexId: string, years: number) {
        const horizonYears: 5 | 10 = years > 5 ? 10 : 5;
        const wkt = this.hexToWkt(hexId);
        return this.repository.fetchByHex(wkt, horizonYears);
    }

    private hexToWkt(hexId: string): string {
        const boundary = cellToBoundary(hexId); // [[lat, lon], ...]
        const ring = boundary.map(([lat, lon]) => `${lon} ${lat}`);
        ring.push(ring[0]); // close the ring
        return `POLYGON((${ring.join(', ')}))`;
    }
}
