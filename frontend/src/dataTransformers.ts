export const normalizeServerData = (serverData: any) => {
  const normalizedData = serverData.map((item: any, index: number) => {
    
    // מושכים את מערך הערים מהשרת (אם אין, נשים מערך ריק)
    const citiesArray = item.cities || [];
    
    // קובעים את שם האזור: נחבר את שמות הערים (למשל "חדרה, אור עקיבא"). אם אין עיר, נרשום "אזור 1"
    const areaName = citiesArray.length > 0 ? citiesArray.join(", ") : `אזור ${index + 1}`;

    return {
      type: "Feature",
      properties: {
        id: index + 1,
        name: areaName,
        // שימי לב: שיניתי פה לחילוק ב-100 כי הציון בתמונה הוא 53! (אם הציון נשאר מתוך 10, תחזירי לחילוק ב-10)
        growth: item.grade / 10, 
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