import { Injectable, NotFoundException } from '@nestjs/common';
import { PropertyFilters, PropertyRepository } from './property.repository';

@Injectable()
export class PropertyService {
  constructor(private readonly repository: PropertyRepository) {}

  findAll(filters: PropertyFilters) {
    return this.repository.findAll(filters);
  }

  findFilterOptions() {
    return this.repository.findFilterOptions();
  }

  async findOne(propertyId: number) {
    const property = await this.repository.findOne(propertyId);
    if (!property) throw new NotFoundException(`Property ${propertyId} was not found`);
    return property;
  }
}
