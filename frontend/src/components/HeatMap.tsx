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

  // 2) Fetch and update heatmap when filters change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const controller = new AbortController();

    async function load() {
      try {
        // Replace this with your real endpoint
        const url = queryString ? `/api/heatmap?${queryString}` : `/api/heatmap`;
        const res = await fetch(url, { signal: controller.signal });

        if (!res.ok) throw new Error(`Heatmap API error: ${res.status}`);

        const geojson = await res.json();

        if (!map) return;
        const src = map.getSource("growth") as GeoJSONSource | undefined;
        if (src) src.setData(geojson);
      } catch (err) {
        // If request was aborted, ignore
        if ((err as any)?.name === "AbortError") return;
        console.error(err);
      }
    }

    // Only load after style & layers exist
    if (map.isStyleLoaded()) {
      load();
    } else {
      map.once("load", load);
    }

    return () => controller.abort();
  }, [queryString]);

  return <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />;
};

export default HeatMap;
