import { Controller, Get, Param, ParseIntPipe, Query } from '@nestjs/common';
import { PropertyFilters } from './property.repository';
import { PropertyService } from './property.service';

function asNumber(value: string | undefined): number | undefined {
  if (value === undefined || value.trim() === '') return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

@Controller('properties')
export class PropertyController {
  constructor(private readonly service: PropertyService) {}

  @Get('filter-options')
  filterOptions() {
    return this.service.findFilterOptions();
  }

  @Get(':propertyId')
  findOne(@Param('propertyId', ParseIntPipe) propertyId: number) {
    return this.service.findOne(propertyId);
  }

  @Get()
  findAll(@Query() query: Record<string, string | undefined>) {
    const poiSource = query.poiSource;
    const filters: PropertyFilters = {
      page: asNumber(query.page),
      pageSize: asNumber(query.pageSize),
      propertyId: asNumber(query.propertyId),
      clusterId: asNumber(query.clusterId),
      search: query.search,
      city: query.city,
      minRooms: asNumber(query.minRooms),
      maxRooms: asNumber(query.maxRooms),
      minBuildingFloors: asNumber(query.minBuildingFloors),
      maxBuildingFloors: asNumber(query.maxBuildingFloors),
      minBuildingYear: asNumber(query.minBuildingYear),
      maxBuildingYear: asNumber(query.maxBuildingYear),
      propertyType: asNumber(query.propertyType),
      minPrice: asNumber(query.minPrice),
      maxPrice: asNumber(query.maxPrice),
      poiTypeId: asNumber(query.poiTypeId),
      poiDistanceMeters: asNumber(query.poiDistanceMeters),
      poiSource: poiSource === 'current' || poiSource === 'future' || poiSource === 'both'
        ? poiSource
        : undefined,
    };

    return this.service.findAll(filters);
  }
}
