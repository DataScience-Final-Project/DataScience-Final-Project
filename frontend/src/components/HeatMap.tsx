// src/components/HeatMap.tsx
import React, { useEffect, useMemo, useRef } from "react";
import maplibregl, { Map as MapLibreMap, GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type Filters = {
  slider?: [number, number];   // price range
  slider2?: [number, number];  // years forward range (as you currently have it)
};

type HeatMapProps = {
  filters: Filters;
};

const HeatMap: React.FC<HeatMapProps> = ({ filters }) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);

  // Build querystring from filters
  const queryString = useMemo(() => {
    const priceMin = filters.slider?.[0];
    const priceMax = filters.slider?.[1];
    const yearsMin = filters.slider2?.[0];
    const yearsMax = filters.slider2?.[1];

    const params = new URLSearchParams();
    if (priceMin !== undefined) params.set("priceMin", String(priceMin));
    if (priceMax !== undefined) params.set("priceMax", String(priceMax));
    if (yearsMin !== undefined) params.set("yearsMin", String(yearsMin));
    if (yearsMax !== undefined) params.set("yearsMax", String(yearsMax));

    return params.toString();
  }, [filters]);

  // 1) Initialize map once
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      // Free style endpoint; you can replace later with your own tiles/style
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [34.7818, 32.0853], // example: Tel Aviv
      zoom: 10,
    });

    mapRef.current = map;

    map.on("load", () => {
      // Add empty source first (so the layer exists even before data arrives)
      map.addSource("growth", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: [],
        },
      });

      map.addLayer({
        id: "growth-heat",
        type: "heatmap",
        source: "growth",
        paint: {
          // Weight is driven by feature property "growth" expected in [0..1]
          "heatmap-weight": [
            "interpolate",
            ["linear"],
            ["coalesce", ["get", "growth"], 0],
            0, 0,
            1, 1,
          ],

          // Heatmap appearance
          "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 8, 1, 14, 3],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 8, 12, 14, 40],
          "heatmap-opacity": 0.85,

          // green -> yellow -> red
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0.0, "rgba(0,0,0,0)",
            0.3, "rgb(0,200,0)",
            0.6, "rgb(255,215,0)",
            1.0, "rgb(220,0,0)",
          ],
        },
      });
    });

    // Optional: navigation controls
    map.addControl(new maplibregl.NavigationControl(), "top-right");

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // 2) Load and update heatmap when filters change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    function load() {
      try {
        // Mock GeoJSON data - replace with actual API call later
        // Note: Currently ignores filters, will use queryString when real endpoint is added
        const geojson = {
          type: "FeatureCollection" as const,
          features: [
            // High growth areas (red/yellow)
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7818, 32.0853] }, properties: { growth: 0.9 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7900, 32.0900] }, properties: { growth: 0.85 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7750, 32.0800] }, properties: { growth: 0.8 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7850, 32.0950] }, properties: { growth: 0.75 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7700, 32.0900] }, properties: { growth: 0.7 } },
            // Medium growth areas (yellow/green)
            { type: "Feature", geometry: { type: "Point", coordinates: [34.8000, 32.1000] }, properties: { growth: 0.6 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7600, 32.0750] }, properties: { growth: 0.55 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7950, 32.0850] }, properties: { growth: 0.5 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7650, 32.1000] }, properties: { growth: 0.45 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.8100, 32.0900] }, properties: { growth: 0.4 } },
            // Lower growth areas (green)
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7500, 32.0700] }, properties: { growth: 0.35 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.8200, 32.1100] }, properties: { growth: 0.3 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7400, 32.1050] }, properties: { growth: 0.25 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.8300, 32.0800] }, properties: { growth: 0.2 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7300, 32.0950] }, properties: { growth: 0.15 } },
            // Additional scattered points
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7800, 32.0700] }, properties: { growth: 0.65 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7900, 32.0750] }, properties: { growth: 0.6 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7700, 32.1050] }, properties: { growth: 0.55 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.8000, 32.0950] }, properties: { growth: 0.5 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7600, 32.0850] }, properties: { growth: 0.45 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7750, 32.1000] }, properties: { growth: 0.4 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7850, 32.0700] }, properties: { growth: 0.35 } },
            { type: "Feature", geometry: { type: "Point", coordinates: [34.7950, 32.1100] }, properties: { growth: 0.3 } },
          ],
        };

        if (!map) return;
        const src = map.getSource("growth") as GeoJSONSource | undefined;
        if (src) src.setData(geojson as any);
      } catch (err) {
        console.error("Error loading heatmap data:", err);
      }
    }

    // Only load after style & layers exist
    if (map.isStyleLoaded()) {
      load();
    } else {
      map.once("load", load);
    }
  }, [queryString]);

  return <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />;
};

export default HeatMap;
