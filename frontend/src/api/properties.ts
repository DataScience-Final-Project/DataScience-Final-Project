const API_BASE_URL = 'http://localhost:4000';

export type PoiSource = 'current' | 'future' | 'both';

export type PropertyListItem = {
  propertyId: number;
  cityName: string | null;
  street: string | null;
  houseNumber: string | null;
  lat: number | null;
  lon: number | null;
  locationAccuracy: number | null;
  numRooms: number | null;
  buildingYear: number | null;
  buildingFloors: number | null;
  propertyType: number | null;
  latestSalePrice: number | null;
  latestSaleDate: string | null;
  clusterId: number | null;
};

export type NearbyPoi = {
  source: 'current' | 'future';
  typeId: number;
  typeName: string;
  plannedYear?: number | null;
  distanceMeters: number;
};

export type PropertyDetails = PropertyListItem & {
  featuresSnapshotYear: number | null;
  featuresHorizonYears: number | null;
  features: Record<string, unknown> | null;
  nearbyPois: NearbyPoi[];
};

export type PropertyFilterOptions = {
  cities: { cityName: string }[];
  propertyTypes: { propertyType: number }[];
  poiTypes: { id: number; name: string }[];
};

export type PropertyFilters = {
  page?: number;
  pageSize?: number;
  propertyId?: number | null;
  clusterId?: number | null;
  search?: string;
  city?: string;
  minRooms?: number | null;
  maxRooms?: number | null;
  minBuildingFloors?: number | null;
  maxBuildingFloors?: number | null;
  minBuildingYear?: number | null;
  maxBuildingYear?: number | null;
  propertyType?: number | null;
  minPrice?: number | null;
  maxPrice?: number | null;
  poiTypeId?: number | null;
  poiSource?: PoiSource;
  poiDistanceMeters?: number | null;
};

export type PropertyPage = {
  items: PropertyListItem[];
  total: number;
  page: number;
  pageSize: number;
};

function toSearchParams(filters: PropertyFilters) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value));
    }
  }
  return params;
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function fetchProperties(filters: PropertyFilters = {}) {
  const query = toSearchParams(filters).toString();
  return request<PropertyPage>(`/properties${query ? `?${query}` : ''}`);
}

export function fetchPropertyDetails(propertyId: number) {
  return request<PropertyDetails>(`/properties/${propertyId}`);
}

export function fetchPropertyFilterOptions() {
  return request<PropertyFilterOptions>('/properties/filter-options');
}
