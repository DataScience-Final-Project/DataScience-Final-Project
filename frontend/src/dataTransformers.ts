import { annualizedGrowthPercent, parseYearsForward } from "./growthMath";

export const normalizeServerData = (serverData: any, yearsForward: string | number = 1) => {
  const years = parseYearsForward(yearsForward);
  const normalizedData = serverData.map((item: any, index: number) => {
    
    // מושכים את מערך הערים מהשרת (אם אין, נשים מערך ריק)
    const citiesArray = item.cities || [];
    
    // קובעים את שם האזור: נחבר את שמות הערים (למשל "חדרה, אור עקיבא"). אם אין עיר, נרשום "אזור 1"
    const areaName = citiesArray.length > 0 ? citiesArray.join(", ") : `אזור ${index + 1}`;

    return {
      type: "Feature",
      properties: {
        id: item.id ?? index + 1,
        clusterId: item.id ?? index + 1,
        name: areaName,
        // Popup: total projected % for selected horizon; map: annualized % (stable color scale)
        growth: annualizedGrowthPercent(item.grade, years),
        originalGrade: item.grade,
        // שומרים את מערך הערים כדי שיוצג ברשימה בפופאפ
        suggestedAreas: citiesArray, 
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          item.coordinates.map((coordinate: any) => [coordinate.x, coordinate.y]),
        ]
      }
    };
  });
  
  return normalizedData;
};
