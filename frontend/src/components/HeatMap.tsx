// src/components/HeatMap.tsx
import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import maplibregl, { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import AreaInvestmentPopup from "./AreaInvestmentPopup";

/** Hebrew / Arabic labels on vector tiles need the RTL shaping plugin (lazy-loaded). */
maplibregl.setRTLTextPlugin(
  "https://unpkg.com/@mapbox/mapbox-gl-rtl-text@0.3.0/dist/mapbox-gl-rtl-text.js",
  true
);

type AreaFeature = {
  type: "Feature";
  geometry: {
    type: "Polygon";
    coordinates: number[][][];
  };
  properties: {
    id?: number;
    clusterId?: number;
    h3Index?: string;
    name?: string;
    neighborhoodName?: string;
    growth: number;
    grade?: number;
    horizonYears?: number;
    originalGrade?: number;
    suggestedAreas?: any;
    [key: string]: any;
  };
};

type HeatMapProps = {
  areas: AreaFeature[];
  /** Increment after a search or reset so the map fits bounds to the current `areas`. */
  fitBoundsNonce?: number;
  selectedClusterId?: number | null;
  /** Increment whenever navigation returns to the map with a selected polygon. */
  selectionNonce?: number;
  isActive?: boolean;
  onAreaSelected?: (clusterId: number, areaName: string) => void;
  onViewProperties?: (clusterId: number, areaName: string) => void;
  /** Called when the user clicks an H3 polygon from the /heatmap feed. */
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

/** Spread colors across the current result set (lowest -> green, highest -> red). */
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

/** Three readable buckets derived from the live color stops (low → high growth). */
function legendLevelsFromStops(stops: [number, string][]): {
  label: string;
  color: string;
  range: string;
}[] {
  const fmt = (v: number) => `${Math.round(v)}%`;
  const lo = stops[0]?.[0] ?? 0;
  const mid = stops[2]?.[0] ?? lo;

  return [
    { label: "High", color: GROWTH_COLOR_PALETTE[4], range: `≥ ${fmt(mid)}` },
    { label: "Medium", color: GROWTH_COLOR_PALETTE[2], range: `${fmt(lo)} – ${fmt(mid)}` },
    { label: "Low", color: GROWTH_COLOR_PALETTE[0], range: `≤ ${fmt(lo)}` },
  ];
}

const HeatMapLegend: React.FC<{ stops: [number, string][] }> = ({ stops }) => {
  const levels = legendLevelsFromStops(stops);
  const gradient = `linear-gradient(90deg, ${GROWTH_COLOR_PALETTE.join(", ")})`;
  const lo = `${Math.round(stops[0]?.[0] ?? 0)}%`;
  const hi = `${Math.round(stops[stops.length - 1]?.[0] ?? 0)}%`;

  return (
    <div className="heatmap-legend" role="img" aria-label="Predicted growth heatmap legend">
      <span className="heatmap-legend__title">Predicted growth</span>

      <div className="heatmap-legend__bar" style={{ background: gradient }} />
      <div className="heatmap-legend__scale">
        <span>{lo}</span>
        <span>{hi}</span>
      </div>

      <ul className="heatmap-legend__levels">
        {levels.map((level) => (
          <li key={level.label} className="heatmap-legend__level">
            <span
              className="heatmap-legend__swatch"
              style={{ backgroundColor: level.color }}
            />
            <span className="heatmap-legend__level-label">{level.label}</span>
            <span className="heatmap-legend__level-range">{level.range}</span>
          </li>
        ))}
      </ul>
    </div>
  );
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

function selectedAreaFeature(areas: AreaFeature[], selectedClusterId: number | null) {
  if (!selectedClusterId) return null;
  return areas.find((area) => Number(area.properties.clusterId ?? area.properties.id) === selectedClusterId) ?? null;
}

function setMapData(map: MapLibreMap, areas: AreaFeature[], selectedClusterId: number | null) {
  const source = map.getSource("growth-source") as GeoJSONSource | undefined;
  if (source) {
    source.setData({
      type: "FeatureCollection",
      features: areas,
    } as any);
  }

  const selectedSource = map.getSource("growth-selected-source") as GeoJSONSource | undefined;
  if (selectedSource) {
    const selectedArea = selectedAreaFeature(areas, selectedClusterId);
    selectedSource.setData({
      type: "FeatureCollection",
      features: selectedArea ? [selectedArea] : [],
    } as any);
  }

  if (map.getLayer("growth-fill")) {
    map.setPaintProperty(
      "growth-fill",
      "fill-color",
      growthFillColorExpression(growthColorStops(areas)),
    );
  }
}

function fitAllAreas(map: MapLibreMap, areas: AreaFeature[]) {
  const bounds = boundsFromPolygonFeatures(areas);
  if (!bounds) return;

  map.resize();
  map.fitBounds(bounds, { padding: 48, maxZoom: 14, duration: 600 });
}

function parseSuggestedAreas(value: unknown) {
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === "string");
  if (typeof value !== "string") return [];

  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : [];
  } catch (error) {
    console.error("Failed to parse suggestedAreas", error);
    return [];
  }
}

const HeatMap: React.FC<HeatMapProps> = ({
  areas,
  fitBoundsNonce = 0,
  selectedClusterId = null,
  selectionNonce = 0,
  isActive = true,
  onAreaSelected,
  onViewProperties,
  onAreaClick,
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const [legendStops, setLegendStops] = useState<[number, string][]>(DEFAULT_ANNUAL_STOPS);
  const onAreaSelectedRef = useRef(onAreaSelected);
  const onViewPropertiesRef = useRef(onViewProperties);
  const onAreaClickRef = useRef(onAreaClick);
  const areasRef = useRef(areas);
  const selectedClusterIdRef = useRef(selectedClusterId);

  useEffect(() => {
    onAreaSelectedRef.current = onAreaSelected;
    onViewPropertiesRef.current = onViewProperties;
    onAreaClickRef.current = onAreaClick;
  }, [onAreaSelected, onViewProperties, onAreaClick]);

  useEffect(() => {
    areasRef.current = areas;
    selectedClusterIdRef.current = selectedClusterId;
  }, [areas, selectedClusterId]);

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

      map.addLayer({
        id: "growth-fill",
        type: "fill",
        source: "growth-source",
        paint: {
          "fill-color": growthFillColorExpression(DEFAULT_ANNUAL_STOPS),
          "fill-opacity": 0.88,
        },
      });

      map.addSource("growth-selected-source", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: [],
        },
      });

      map.addLayer({
        id: "growth-outline",
        type: "line",
        source: "growth-source",
        paint: {
          "line-color": "#ffffff",
          "line-width": 1,
          "line-opacity": 0.75,
        },
      });

      map.addLayer({
        id: "growth-selected-outline",
        type: "line",
        source: "growth-selected-source",
        paint: {
          "line-color": "#c4b5fd",
          "line-width": 4,
          "line-opacity": 1,
        },
      });

      setMapData(map, areasRef.current, selectedClusterIdRef.current);
      if (selectedClusterIdRef.current) {
        requestAnimationFrame(() => fitAllAreas(map, areasRef.current));
      }

      map.on("mouseenter", "growth-fill", () => {
        map.getCanvas().style.cursor = "pointer";
      });

      map.on("mouseleave", "growth-fill", () => {
        map.getCanvas().style.cursor = "";
      });

      map.on("click", "growth-fill", (event) => {
        const selectedFeature = event.features?.[0];
        if (!selectedFeature) return;

        const properties = selectedFeature.properties as AreaFeature["properties"];
        const areaName = properties.name || properties.neighborhoodName || "Selected area";
        const clusterId = Number(properties.clusterId ?? properties.id);
        const h3Index = typeof properties.h3Index === "string" ? properties.h3Index : null;
        const gradeValue = properties.originalGrade !== undefined
          ? Number(properties.originalGrade)
          : Number(properties.grade ?? properties.growth ?? 0);
        const horizonYears = Number(properties.horizonYears ?? 5);
        const suggestedAreas = parseSuggestedAreas(properties.suggestedAreas);

        if (Number.isFinite(clusterId)) {
          onAreaSelectedRef.current?.(clusterId, areaName);
        }

        const popupContainer = document.createElement("div");
        const popupRoot = createRoot(popupContainer);
        const handleViewProperties = h3Index && onAreaClickRef.current
          ? () => onAreaClickRef.current?.(h3Index, areaName)
          : Number.isFinite(clusterId)
            ? () => onViewPropertiesRef.current?.(clusterId, areaName)
            : undefined;

        popupRoot.render(
          <AreaInvestmentPopup
            areaName={areaName}
            growthPercent={gradeValue}
            horizonYears={horizonYears}
            suggestedAreas={suggestedAreas}
            onViewProperties={handleViewProperties}
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

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    function update() {
      setMapData(map!, areas, selectedClusterId);
      const geojson = {
        type: "FeatureCollection",
        features: areas,
      };

      const src = map?.getSource("growth-source") as GeoJSONSource | undefined;
      if (src) src.setData(geojson as any);

      const stops = growthColorStops(areas);
      setLegendStops(stops);

      if (map?.getLayer("growth-fill")) {
        map.setPaintProperty(
          "growth-fill",
          "fill-color",
          growthFillColorExpression(stops),
        );
      }
    }

    if (map.isStyleLoaded()) {
      update();
    } else {
      map.once("load", update);
    }
  }, [areas, selectedClusterId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isActive || !selectedClusterId) return;
    const selectedArea = selectedAreaFeature(areas, selectedClusterId);
    if (!selectedArea) return;

    const fit = () => {
      setMapData(map, areas, selectedClusterId);
      fitAllAreas(map, areas);
    };

    if (map.isStyleLoaded()) requestAnimationFrame(fit);
    else map.once("load", fit);
  }, [areas, isActive, selectedClusterId, selectionNonce]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || fitBoundsNonce === 0 || !areas.length) return;

    function fit() {
      fitAllAreas(map!, areas);
    }

    if (map.isStyleLoaded()) {
      fit();
    } else {
      map.once("load", fit);
    }
  }, [areas, fitBoundsNonce]);

  return (
    <div className="heatmap-stage" style={{ position: "relative", width: "100%", height: "100%" }}>
      <HeatMapLegend stops={legendStops} />
      <div ref={mapContainerRef} className="heatmap-canvas" style={{ width: "100%", height: "100%" }} />
    </div>
  );
};

export default HeatMap;
