import { BadRequestException, Injectable, NotFoundException } from "@nestjs/common";
import { InjectModel } from "@nestjs/sequelize";
import type { CreateSavedSearchRequest } from "./savedSearch.dto";
import { SavedSearch, type SearchFilters } from "./savedSearch.model";

export type PublicSavedSearch = {
    id: string;
    name: string;
    filters: SearchFilters;
    createdAt: string;
};

@Injectable()
export class SavedSearchService {
    constructor(
        @InjectModel(SavedSearch) private readonly savedSearchModel: typeof SavedSearch,
    ) { }

    async list(userId: number): Promise<PublicSavedSearch[]> {
        const rows = await this.savedSearchModel.findAll({
            where: { userId },
            order: [['created_at', 'DESC']],
        });

        return rows.map(row => this.toPublic(row));
    }

    async create(userId: number, dto: CreateSavedSearchRequest): Promise<PublicSavedSearch> {
        const filters = dto.filters;
        if (!filters || typeof filters !== 'object') {
            throw new BadRequestException('filters is required');
        }

        const name = dto.name?.trim() || 'Untitled search';
        const created = await this.savedSearchModel.create({ userId, name, filters });

        return this.toPublic(created);
    }

    async remove(userId: number, id: string): Promise<void> {
        const deleted = await this.savedSearchModel.destroy({ where: { id, userId } });
        if (deleted === 0) {
            throw new NotFoundException('Saved search not found');
        }
    }

    private toPublic(row: SavedSearch): PublicSavedSearch {
        return {
            id: String(row.id),
            name: row.name,
            filters: row.filters,
            createdAt: row.createdAt.toISOString(),
        };
    }
}
