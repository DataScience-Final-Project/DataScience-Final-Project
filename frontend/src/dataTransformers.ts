import { annualizedGrowthPercent, parseYearsForward } from "./growthMath";

export const normalizeServerData = (serverData: any, yearsForward: string | number = 1) => {
  const years = parseYearsForward(yearsForward);

  // New format: FeatureCollection from POST /heatmap
  if (serverData && serverData.type === 'FeatureCollection' && Array.isArray(serverData.features)) {
    return serverData.features.map((feature: any) => ({
      ...feature,
      properties: {
        ...feature.properties,
        growth: annualizedGrowthPercent(feature.properties.grade, feature.properties.horizonYears ?? years),
      },
    }));
  }

  // Flat array from GET /neighborhood-predictions (geom is a GeoJSON geometry object)
  return serverData.map((item: any, index: number) => {
    if (item.geom && typeof item.geom === 'object') {
      const name = item.cityName || item.neighborhoodName || `אזור ${index + 1}`;
      const horizonYears: number = item.horizonYears || 5;
      return {
        type: "Feature",
        properties: {
          id: index + 1,
          name,
          neighborhoodName: item.neighborhoodName ?? null,
          priceNow: item.priceNow ?? null,
          growth: annualizedGrowthPercent(item.grade, horizonYears),
          originalGrade: item.grade,
          suggestedAreas: item.cityName ? [item.cityName] : [],
        },
        geometry: item.geom,
      };
    }

    // Legacy format: growth_clusters (coordinates as {x,y}[])
    const citiesArray = item.cities || [];
    const areaName = citiesArray.length > 0 ? citiesArray.join(", ") : `אזור ${index + 1}`;
    return {
      type: "Feature",
      properties: {
        id: index + 1,
        name: areaName,
        growth: annualizedGrowthPercent(item.grade, years),
        originalGrade: item.grade,
        suggestedAreas: citiesArray,
      },
      geometry: {
        type: "Polygon",
        coordinates: [item.coordinates.map((c: any) => [c.x, c.y])],
      },
    };
  });
};
