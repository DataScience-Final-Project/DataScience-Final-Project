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

  return [];
};
