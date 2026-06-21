// src/components/HeatMap.tsx
import React, { useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import maplibregl, { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// הסרנו את הייבוא של נתוני הדמה, משאירים רק את הקומפוננטה
import AreaInvestmentPopup from "./AreaInvestmentPopup";

/** Hebrew / Arabic labels on vector tiles need the RTL shaping plugin (lazy-loaded). */
maplibregl.setRTLTextPlugin(
  "https://unpkg.com/@mapbox/mapbox-gl-rtl-text@0.3.0/dist/mapbox-gl-rtl-text.js",
  true
);

// עדכון ה-Type: פוליגון דורש מערך תלת-ממדי של מספרים
type AreaFeature = {
  type: "Feature";
  geometry: {
    type: "Polygon";
    coordinates: number[][][]; // מערך של טבעות קואורדינטות
  };
  properties: {
    id?: number;
    name?: string;
    growth: number;
    originalGrade?: number; // הוספנו את הציון המקורי ל-Type
    suggestedAreas?: any; // הוספנו את מערך הערים
    [key: string]: any;
  };
};

type HeatMapProps = {
  areas: AreaFeature[];
  /** Increment after a search or reset so the map fits bounds to the current `areas`. */
  fitBoundsNonce?: number;
  /** Called when the user clicks a hex polygon. Receives the raw H3 index and a display name. */
  onAreaClick?: (h3Index: string, areaDisplayName: string) => void;
};

const GROWTH_COLOR_PALETTE = ["#16a34a", "#4ade80", "#facc15", "#ef4444", "#b91c1c"] as const;
const GROWTH_QUANTILES = [0, 0.25, 0.5, 0.75, 1] as const;

const DEFAULT_ANNUAL_STOPS: [number, string][] = [
  [0, GROWTH_COLOR_PALETTE[0]],
  [4, GROWTH_COLOR_PALETTE[1]],
  [8, GROWTH_COLOR_PALETTE[2]],
  [12, GROWTH_COLOR_PALETTE[3]],
  [16, GROWTH_COLOR_PALETTE[4]],
];

function growthValues(features: AreaFeature[]): number[] {
  return features
    .map((f) => Number(f.properties.growth))
    .filter((v) => Number.isFinite(v))
    .sort((a, b) => a - b);
}

/** Spread colors across the current result set (lowest → green, highest → red). */
function growthColorStops(features: AreaFeature[]): [number, string][] {
  const values = growthValues(features);
  if (!values.length) return DEFAULT_ANNUAL_STOPS;

  const pick = (p: number) => values[Math.min(values.length - 1, Math.round(p * (values.length - 1)))];

  const stops: [number, string][] = GROWTH_QUANTILES.map((p, i) => [pick(p), GROWTH_COLOR_PALETTE[i]]);

  for (let i = 1; i < stops.length; i++) {
    if (stops[i][0] <= stops[i - 1][0]) {
      stops[i] = [stops[i - 1][0] + 0.001, stops[i][1]];
    }
  }
  return stops;
}

function growthFillColorExpression(stops: [number, string][]): maplibregl.ExpressionSpecification {
  const growth: maplibregl.ExpressionSpecification = ["to-number", ["get", "growth"]];
  return ["interpolate-hcl", ["linear"], growth, ...stops.flat()];
}

function boundsFromPolygonFeatures(features: AreaFeature[]): maplibregl.LngLatBounds | null {
  const bounds = new maplibregl.LngLatBounds();
  let hasPoint = false;
  for (const f of features) {
    if (f.geometry.type !== "Polygon") continue;
    for (const ring of f.geometry.coordinates) {
      for (const pt of ring) {
        const [lng, lat] = pt;
        bounds.extend([lng, lat]);
        hasPoint = true;
      }
    }
  }
  return hasPoint ? bounds : null;
}

const HeatMap: React.FC<HeatMapProps> = ({ areas, fitBoundsNonce = 0, onAreaClick }) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [34.7818, 32.0853],
      zoom: 8,
    });

    mapRef.current = map;

    map.on("load", () => {
      map.addSource("growth-source", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: [],
        },
      });

      // 1. שכבת המילוי (הצבע ה"חם")
      map.addLayer({
        id: "growth-fill",
        type: "fill", // שינוי מ-heatmap ל-fill
        source: "growth-source",
        paint: {
          "fill-color": growthFillColorExpression(DEFAULT_ANNUAL_STOPS),
          "fill-opacity": 0.88,
        },
      });

      // 2. שכבת קווי מתאר (כדי שהאזורים יהיו מובחנים)
      map.addLayer({
        id: "growth-outline",
        type: "line",
        source: "growth-source",
        paint: {
          "line-color": "#ffffff",
          "line-width": 1,
          "line-opacity": 0.75
        }
      });

      map.on("mouseenter", "growth-fill", () => {
        map.getCanvas().style.cursor = "pointer";
      });

      map.on("mouseleave", "growth-fill", () => {
        map.getCanvas().style.cursor = "";
      });

      map.on("click", "growth-fill", (event) => {
        const selectedFeature = event.features?.[0];
        if (!selectedFeature) return;

        const properties = selectedFeature.properties as any;

        const areaName = properties.name || properties.neighborhoodName || "Selected area";
        const h3Index: string | null = properties.h3Index ?? null;

        if (h3Index && onAreaClick) {
          onAreaClick(h3Index, areaName);
        }
        
        // Use grade (total % over horizon) so it matches the per-property percentChange values
        const gradeValue = Number(properties.grade ?? properties.growth ?? 0);
        const horizonYears: number = Number(properties.horizonYears ?? 5);

        // --- הפיכת הערים ממחרוזת של MapLibre למערך אמיתי ---
        let parsedCities: string[] = [];
        try {
          if (typeof properties.suggestedAreas === "string") {
            parsedCities = JSON.parse(properties.suggestedAreas);
          } else if (Array.isArray(properties.suggestedAreas)) {
            parsedCities = properties.suggestedAreas;
          }
        } catch (e) {
          console.error("Failed to parse suggestedAreas", e);
          parsedCities = [];
        }
        // ----------------------------------------------------

        const popupContainer = document.createElement("div");
        const popupRoot = createRoot(popupContainer);

        popupRoot.render(
          <AreaInvestmentPopup
            areaName={areaName}
            growthPercent={gradeValue}
            horizonYears={horizonYears}
            suggestedAreas={parsedCities}
          />
        );

        popupRef.current?.remove();
        const popup = new maplibregl.Popup({
          closeOnClick: true,
          maxWidth: "260px",
          anchor: "bottom",
          offset: 12,
        })
          .setLngLat(event.lngLat)
          .setDOMContent(popupContainer)
          .addTo(map);

        popup.on("close", () => {
          popupRoot.unmount();
        });

        popupRef.current = popup;
      });
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");

    return () => {
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // עדכון הנתונים כשה-areas משתנים
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    function update() {
      const geojson = {
        type: "FeatureCollection",
        features: areas,
      };

      const src = map?.getSource("growth-source") as GeoJSONSource | undefined;
      if (src) src.setData(geojson as any);

      if (map?.getLayer("growth-fill")) {
        map.setPaintProperty(
          "growth-fill",
          "fill-color",
          growthFillColorExpression(growthColorStops(areas)),
        );
      }
    }

    if (map.isStyleLoaded()) {
      update();
    } else {
      map.once("load", update);
    }
  }, [areas]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || fitBoundsNonce === 0 || !areas.length) return;

    function fit() {
      const b = boundsFromPolygonFeatures(areas);
      if (!b || !map) return;
      map.fitBounds(b, { padding: 48, maxZoom: 14, duration: 600 });
    }

    if (map.isStyleLoaded()) {
      fit();
    } else {
      map.once("load", fit);
    }
  }, [areas, fitBoundsNonce]);

  return <div ref={mapContainerRef} className="heatmap-canvas" style={{ width: "100%", height: "100%" }} />;
};

export default HeatMap;