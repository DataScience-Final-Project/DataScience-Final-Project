import { annualizedGrowthPercent, parseYearsForward } from "./growthMath";

export const normalizeServerData = (serverData: any, yearsForward: string | number = 1) => {
  const years = parseYearsForward(yearsForward);

  if (serverData && serverData.type === 'FeatureCollection' && Array.isArray(serverData.features)) {
    return serverData.features.map((feature: any) => ({
      ...feature,
      properties: {
        ...feature.properties,
        growth: annualizedGrowthPercent(feature.properties.grade ?? feature.properties.growth ?? 0, feature.properties.horizonYears ?? years),
      },
    }));
  }

  const rows = Array.isArray(serverData) ? serverData : [];

  return rows.map((item: any, index: number) => {
    const citiesArray = item.cities || [];
    const areaName = citiesArray.length > 0 ? citiesArray.join(", ") : `אזור ${index + 1}`;

    return {
      type: "Feature",
      properties: {
        id: item.id ?? index + 1,
        clusterId: item.id ?? index + 1,
        name: areaName,
        growth: annualizedGrowthPercent(item.grade, years),
        originalGrade: item.grade,
        suggestedAreas: citiesArray,
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          item.coordinates.map((coordinate: any) => [coordinate.x, coordinate.y]),
        ],
      },
    };
  });
};
