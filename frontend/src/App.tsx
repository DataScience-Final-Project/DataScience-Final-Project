import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeftOutlined, LogoutOutlined } from '@ant-design/icons';
import { Button, Card, ConfigProvider, Tabs, message } from 'antd';
import FiltersForm from './components/FiltersForm';
import HeatMap from './components/HeatMap';
import PolygonPropertiesPanel from './components/PolygonPropertiesPanel';
import PropertiesTab from './components/PropertiesTab';
import SavedSearches from './components/SavedSearches';
import propCastLogo from './assets/propCastLogo.png';
import './App.css';
import { dashboardTheme } from './dashboardTheme';
import { normalizeServerData } from './dataTransformers';
import type { SearchFilters } from './api/personalization';
import type { PropertyListItem } from './api/properties';
import { getCurrentUser, clearCurrentUser } from './api/auth';

type DashboardTab = 'map' | 'properties';

type NavigationState = {
  tab: DashboardTab;
  propertyId: number | null;
  clusterId: number | null;
  areaName: string | null;
};

type MapArea = {
  type: 'Feature';
  geometry: {
    type: 'Polygon';
    coordinates: number[][][];
  };
  properties: {
    id?: number;
    clusterId?: number;
    name?: string;
    growth: number;
    originalGrade?: number;
    suggestedAreas?: unknown;
    [key: string]: unknown;
  };
};

function parsePositiveInteger(value: string | null) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function parseDashboardTab(value: string | null): DashboardTab {
  return value === 'properties' ? 'properties' : 'map';
}

function areaClusterId(area: MapArea) {
  return Number(area.properties.clusterId ?? area.properties.id);
}

function areaDisplayName(area: MapArea) {
  return area.properties.name ?? null;
}

const App = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const currentUser = getCurrentUser();
  const [filtersFormState, setFiltersFormState] = useState<SearchFilters>({ yearsForward: '5' });
  const [mapAreas, setMapAreas] = useState<MapArea[]>([]);
  const [mapFitNonce, setMapFitNonce] = useState(0);
  const [appliedValues, setAppliedValues] = useState<SearchFilters | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const isInitialFetchRef = useRef(true);
  const selectedClusterFetchRef = useRef<number | null>(null);
  const navigationHistoryRef = useRef<NavigationState[]>([]);
  const [activeTab, setActiveTab] = useState<DashboardTab>(
    () => parseDashboardTab(searchParams.get('tab')),
  );
  const [selectedPropertyId, setSelectedPropertyId] = useState<number | null>(
    () => parsePositiveInteger(searchParams.get('propertyId')),
  );
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(
    () => parsePositiveInteger(searchParams.get('clusterId')),
  );
  const [selectedAreaName, setSelectedAreaName] = useState<string | null>(
    () => searchParams.get('areaName'),
  );
  const [mapSelectionNonce, setMapSelectionNonce] = useState(0);
  const [canGoBack, setCanGoBack] = useState(false);
  const selectedAreaFromMap = selectedClusterId
    ? mapAreas.find((area) => areaClusterId(area) === selectedClusterId)
    : undefined;
  const selectedAreaDisplayName = selectedAreaName ?? (selectedAreaFromMap ? areaDisplayName(selectedAreaFromMap) : null);

  const currentNavigationState = (): NavigationState => ({
    tab: activeTab,
    propertyId: selectedPropertyId,
    clusterId: selectedClusterId,
    areaName: selectedAreaDisplayName,
  });

  const navigateToTab = (next: NavigationState) => {
    const current = currentNavigationState();
    const isSameDestination = current.tab === next.tab
      && current.propertyId === next.propertyId
      && current.clusterId === next.clusterId;
    if (isSameDestination) return;

    navigationHistoryRef.current.push(current);
    setCanGoBack(true);
    setActiveTab(next.tab);
    setSelectedPropertyId(next.propertyId);
    setSelectedClusterId(next.clusterId);
    setSelectedAreaName(next.areaName);
    if (next.tab === 'map' && next.clusterId) setMapSelectionNonce((nonce) => nonce + 1);
  };

  const goBack = () => {
    const previous = navigationHistoryRef.current.pop();
    if (!previous) return;
    setActiveTab(previous.tab);
    setSelectedPropertyId(previous.propertyId);
    setSelectedClusterId(previous.clusterId);
    setSelectedAreaName(previous.areaName);
    if (previous.tab === 'map' && previous.clusterId) setMapSelectionNonce((nonce) => nonce + 1);
    setCanGoBack(navigationHistoryRef.current.length > 0);
  };

  const propertyDetailsUrl = (propertyId: number, returnToMap: boolean) => {
    const params = new URLSearchParams();

    if (returnToMap && selectedClusterId) {
      params.set('returnTo', 'map');
      params.set('clusterId', String(selectedClusterId));
      if (selectedAreaDisplayName) params.set('areaName', selectedAreaDisplayName);
    }

    const query = params.toString();
    return `/dashboard/properties/${propertyId}${query ? `?${query}` : ''}`;
  };

  const handleLogout = () => {
    clearCurrentUser();
    navigate('/');
  };

  useEffect(() => {
    const fetchMapArea = async () => {
      const years = filtersFormState.yearsForward?.replace('+', '') || '5';
      let url = `http://localhost:4000/growth-clusters?years=${years}`;

      if (filtersFormState.city) {
        url += `&city=${encodeURIComponent(filtersFormState.city)}`;
      }
      if (filtersFormState.slider && filtersFormState.slider.length === 2) {
        url += `&minPrice=${filtersFormState.slider[0]}&maxPrice=${filtersFormState.slider[1]}`;
      }

      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        const resAsJson = await res.json();
        if (!resAsJson || resAsJson.length === 0) {
          message.warning('לא נמצאו אזורי השקעה שמתאימים לסינון. נסה לשנות אזור או תקציב.');
          setMapAreas([]);
          if (!isInitialFetchRef.current) setMapFitNonce((n) => n + 1);
          return;
        }

        setMapAreas(normalizeServerData(resAsJson, years) as MapArea[]);
        if (!isInitialFetchRef.current) setMapFitNonce((n) => n + 1);
      } catch (error) {
        console.error('Fetch error:', error);
        message.error('שגיאה בתקשורת מול השרת. ודאי שהשרת רץ.');
      } finally {
        isInitialFetchRef.current = false;
      }
    };

    fetchMapArea();
  }, [filtersFormState]);

  useEffect(() => {
    if (activeTab !== 'map' || !selectedClusterId) return;

    const existingArea = mapAreas.find((area) => areaClusterId(area) === selectedClusterId);
    if (existingArea) return;

    if (selectedClusterFetchRef.current === selectedClusterId) return;

    const controller = new AbortController();
    selectedClusterFetchRef.current = selectedClusterId;

    const fetchSelectedCluster = async () => {
      const years = filtersFormState.yearsForward?.replace('+', '') || '5';

      try {
        const response = await fetch(
          `http://localhost:4000/growth-clusters?years=${years}&clusterId=${selectedClusterId}`,
          { signal: controller.signal },
        );
        if (!response.ok) throw new Error(`Request failed (${response.status})`);
        const [area] = normalizeServerData(await response.json(), years) as MapArea[];
        if (!area) return;

        setMapAreas((current) => {
          if (current.some((currentArea) => areaClusterId(currentArea) === selectedClusterId)) {
            return current;
          }
          return [...current, area];
        });
      } catch (error) {
        if (!controller.signal.aborted) {
          console.error('Could not load the selected polygon', error);
          message.error('Could not load the selected polygon.');
        }
      } finally {
        if (selectedClusterFetchRef.current === selectedClusterId) {
          selectedClusterFetchRef.current = null;
        }
      }
    };

    fetchSelectedCluster();

    return () => {
      controller.abort();
    };
  }, [activeTab, filtersFormState.yearsForward, mapAreas, selectedClusterId]);

  const onFinish = (values: SearchFilters) => {
    setFiltersFormState(values);
    setHasSubmitted(true);
  };

  const handleApplySavedSearch = (filters: SearchFilters) => {
    const values = { ...filters };
    setAppliedValues(values);
    setFiltersFormState(values);
    setHasSubmitted(true);
  };

  const handlePolygonSelected = (clusterId: number, areaName: string) => {
    setSelectedClusterId(clusterId);
    setSelectedAreaName(areaName);
  };

  const handleOpenProperty = (propertyId: number) => {
    navigate(propertyDetailsUrl(propertyId, selectedClusterId !== null));
  };

  const handleViewPolygon = async (property: PropertyListItem) => {
    if (!property.clusterId) return;
    let area = mapAreas.find((mapArea) => areaClusterId(mapArea) === property.clusterId);

    if (!area) {
      const years = filtersFormState.yearsForward?.replace('+', '') || '5';
      try {
        const response = await fetch(`http://localhost:4000/growth-clusters?years=${years}&clusterId=${property.clusterId}`);
        if (!response.ok) throw new Error(`Request failed (${response.status})`);
        const result = normalizeServerData(await response.json(), years) as MapArea[];
        const loadedArea = result[0];
        if (loadedArea) {
          area = loadedArea;
          setMapAreas((current) => [...current, loadedArea]);
        }
      } catch (error) {
        console.error('Could not load the property polygon', error);
        message.error('Could not load the polygon for this property.');
      }
    }

    navigateToTab({
      tab: 'map',
      propertyId: property.propertyId,
      clusterId: property.clusterId,
      areaName: area ? areaDisplayName(area) : null,
    });
  };

  const currentFilters: SearchFilters = {
    city: filtersFormState.city,
    slider: filtersFormState.slider,
    yearsForward: filtersFormState.yearsForward,
    roomsRange: filtersFormState.roomsRange,
  };

  return (
    <ConfigProvider theme={dashboardTheme}>
      <div className="app-shell">
        <header className="dashboard-header">
          {currentUser && <div className="dashboard-welcome">Welcome, {currentUser.firstName}</div>}
          <div className="dashboard-brand"><img src={propCastLogo} alt="PropCast" /></div>
          <Button className="dashboard-logout" icon={<LogoutOutlined />} onClick={handleLogout}>Log out</Button>
        </header>

        <main className="dashboard-main">
          <Tabs
            className="dashboard-tabs"
            activeKey={activeTab}
            onChange={(tab) => navigateToTab({
              tab: tab as DashboardTab,
              propertyId: tab === 'properties' ? selectedPropertyId : null,
              clusterId: selectedClusterId,
              areaName: selectedAreaDisplayName,
            })}
            tabBarExtraContent={canGoBack ? (
              <Button icon={<ArrowLeftOutlined />} onClick={goBack}>Back</Button>
            ) : null}
            items={[
              {
                key: 'map',
                label: 'Market map',
                children: (
                  <div className="dashboard-grid">
                    <div className="dashboard-left-col">
                      <Card className="dashboard-card dashboard-card--filters" bordered={false} title="Filters">
                        <FiltersForm onFinish={onFinish} appliedValues={appliedValues} />
                      </Card>
                      <Card className="dashboard-card dashboard-card--saved" bordered={false} title="Saved searches">
                        <SavedSearches currentFilters={currentFilters} canSave={hasSubmitted} onApply={handleApplySavedSearch} />
                      </Card>
                    </div>
                    <div className="dashboard-map-column">
                      <Card className="dashboard-card dashboard-card--map" bordered={false} title="Market map">
                        <div className="heatmap-shell">
                          <HeatMap
                            areas={mapAreas}
                            fitBoundsNonce={mapFitNonce}
                            selectedClusterId={selectedClusterId}
                            selectionNonce={mapSelectionNonce}
                            isActive={activeTab === 'map'}
                            onAreaSelected={handlePolygonSelected}
                            onViewProperties={(clusterId, areaName) => {
                              navigateToTab({ tab: 'properties', propertyId: null, clusterId, areaName });
                            }}
                          />
                        </div>
                      </Card>
                      <PolygonPropertiesPanel
                        clusterId={selectedClusterId}
                        areaName={selectedAreaDisplayName}
                        onOpenProperty={handleOpenProperty}
                      />
                    </div>
                  </div>
                ),
              },
              {
                key: 'properties',
                label: 'Properties',
                children: (
                  <PropertiesTab
                    selectedPropertyId={selectedPropertyId}
                    selectedClusterId={selectedClusterId}
                    selectedAreaName={selectedAreaDisplayName}
                    onClearSelectedProperty={() => setSelectedPropertyId(null)}
                    onClearSelectedPolygon={() => {
                      setSelectedClusterId(null);
                      setSelectedAreaName(null);
                    }}
                    onOpenProperty={handleOpenProperty}
                    onViewPolygon={handleViewPolygon}
                  />
                ),
              },
            ]}
          />
        </main>
      </div>
    </ConfigProvider>
  );
};

export default App;
