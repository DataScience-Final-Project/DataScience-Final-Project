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
};

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

const HeatMap: React.FC<HeatMapProps> = ({ areas, fitBoundsNonce = 0 }) => {
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
          "fill-color": [
            "interpolate",
            ["linear"],
            ["get", "growth"],
            0.4, "#64e37f",
            0.7, "#ffcf54",
            0.9, "#fc6a6a"
          ],
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
        
        const areaName = properties.name || "Selected area";
        
        // אנחנו משתמשים בציון המקורי אם הוא קיים, אחרת מכפילים ב-100 (לפי הסקאלה החדשה)
        const gradeValue = properties.originalGrade !== undefined 
            ? properties.originalGrade 
            : Number(properties.growth ?? 0) * 10; 

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
            suggestedAreas={parsedCities} // מעבירים את המערך האמיתי מהשרת!
          />
        );

        popupRef.current?.remove();
        const popup = new maplibregl.Popup({ closeOnClick: true, maxWidth: "320px" })
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