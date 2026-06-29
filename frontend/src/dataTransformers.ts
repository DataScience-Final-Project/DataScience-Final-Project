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

  return [];
};
