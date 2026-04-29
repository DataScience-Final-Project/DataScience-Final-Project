export const normalizeServerData = (serverData: any) => {
    
    const normalizedData = serverData.map((item: any, index: number) => {
      return {
        type: "Feature",
        properties: {
          id: index + 1, 
          name: `Area ${index + 1}`, 
          growth: item.grade / 10,
          originalGrade: item.grade,
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