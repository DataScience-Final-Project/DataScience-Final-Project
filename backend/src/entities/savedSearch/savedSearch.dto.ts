import type { SearchFilters } from "./savedSearch.model";

export type CreateSavedSearchRequest = {
    name?: string;
    filters?: SearchFilters;
};
