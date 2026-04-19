// src/data.tsx

export const mockAreas = [
  {
    type: "Feature",
    properties: {
      id: 1,
      name: "Central Tel Aviv (Irregular)",
      growth: 0.9, 
    },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [34.768, 32.065],
          [34.775, 32.060],
          [34.785, 32.068],
          [34.790, 32.078],
          [34.782, 32.085],
          [34.770, 32.080],
          [34.765, 32.072],
          [34.768, 32.065], // Closes the shape
        ],
      ],
    },
  },
  {
    type: "Feature",
    properties: {
      id: 2,
      name: "Ramat Gan Area (Irregular)",
      growth: 0.5, 
    },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [34.800, 32.065],
          [34.815, 32.062],
          [34.825, 32.075],
          [34.820, 32.088],
          [34.805, 32.090],
          [34.795, 32.082],
          [34.798, 32.072],
          [34.800, 32.065], 
        ],
      ],
    },
  },
  {
    type: "Feature",
    properties: {
      id: 3,
      name: "Jaffa Coastline (Irregular)",
      growth: 0.1, 
    },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [34.748, 32.040],
          [34.755, 32.035],
          [34.768, 32.042],
          [34.765, 32.052],
          [34.758, 32.055],
          [34.750, 32.050],
          [34.748, 32.040], 
        ],
      ],
    },
  },
  {
    type: "Feature",
    properties: {
      id: 4,
      name: "North Areas (Irregular)",
      growth: 0.75, 
    },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [34.780, 32.095],
          [34.795, 32.092],
          [34.808, 32.105],
          [34.802, 32.118],
          [34.785, 32.120],
          [34.775, 32.110],
          [34.780, 32.095], 
        ],
      ],
    },
  },
] as any;