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
import { getCurrentUser, clearCurrentUser } from './api/auth';

type DashboardTab = 'map' | 'properties';

type FormState = SearchFilters & {
  floorsRange?: [number, number];
  minGrowth?: number;
  poiFilters?: { poiTypeId: number; maxDistanceMeters: number }[];
};

type NavigationState = {
  tab: DashboardTab;
  propertyId: number | null;
  hexId: string | null;
  areaName: string | null;
};

type MapArea = {
  type: 'Feature';
  geometry: { type: 'Polygon'; coordinates: number[][][] };
  properties: {
    h3Index?: string;
    name?: string;
    neighborhoodName?: string;
    growth: number;
    horizonYears?: number;
    suggestedAreas?: unknown;
    [key: string]: unknown;
  };
};

function parseDashboardTab(value: string | null): DashboardTab {
  return value === 'properties' ? 'properties' : 'map';
}

const App = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const currentUser = getCurrentUser();

  const [filtersFormState, setFiltersFormState] = useState<FormState>({ yearsForward: '5' });
  const [mapAreas, setMapAreas] = useState<MapArea[]>([]);
  const [mapFitNonce, setMapFitNonce] = useState(0);
  const [appliedValues, setAppliedValues] = useState<FormState | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const isInitialFetchRef = useRef(true);
  const navigationHistoryRef = useRef<NavigationState[]>([]);

  const [activeTab, setActiveTab] = useState<DashboardTab>(
    () => parseDashboardTab(searchParams.get('tab')),
  );
  const [selectedPropertyId, setSelectedPropertyId] = useState<number | null>(null);
  const [selectedHexId, setSelectedHexId] = useState<string | null>(null);
  const [selectedAreaName, setSelectedAreaName] = useState<string | null>(null);
  const [canGoBack, setCanGoBack] = useState(false);

  const currentNavigationState = (): NavigationState => ({
    tab: activeTab,
    propertyId: selectedPropertyId,
    hexId: selectedHexId,
    areaName: selectedAreaName,
  });

  const navigateToTab = (next: NavigationState) => {
    const current = currentNavigationState();
    const isSameDestination =
      current.tab === next.tab &&
      current.propertyId === next.propertyId &&
      current.hexId === next.hexId;
    if (isSameDestination) return;

    navigationHistoryRef.current.push(current);
    setCanGoBack(true);
    setActiveTab(next.tab);
    setSelectedPropertyId(next.propertyId);
    setSelectedHexId(next.hexId);
    setSelectedAreaName(next.areaName);
  };

  const goBack = () => {
    const previous = navigationHistoryRef.current.pop();
    if (!previous) return;
    setActiveTab(previous.tab);
    setSelectedPropertyId(previous.propertyId);
    setSelectedHexId(previous.hexId);
    setSelectedAreaName(previous.areaName);
    setCanGoBack(navigationHistoryRef.current.length > 0);
  };

  const propertyDetailsUrl = (propertyId: number, returnToMap: boolean) => {
    const params = new URLSearchParams();
    if (returnToMap && selectedHexId) {
      params.set('returnTo', 'map');
      params.set('hexId', selectedHexId);
      if (selectedAreaName) params.set('areaName', selectedAreaName);
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
      const [minPrice, maxPrice]: [number, number] = filtersFormState.slider ?? [0, 10_000_000];
      const [minRooms, maxRooms]: [number, number] = filtersFormState.roomsRange ?? [1, 10];
      const [minFloors, maxFloors]: [number, number] = filtersFormState.floorsRange ?? [0, 30];
      const minGrowth = filtersFormState.minGrowth ?? 0;

      const body: Record<string, any> = { years: Number(years) };
      if (filtersFormState.city)  body.city = filtersFormState.city;
      if (minPrice > 0)           body.minPrice = minPrice;
      if (maxPrice < 10_000_000)  body.maxPrice = maxPrice;
      if (minRooms > 1)           body.minRooms = minRooms;
      if (maxRooms < 10)          body.maxRooms = maxRooms;
      if (minFloors > 0)          body.minFloors = minFloors;
      if (maxFloors < 30)         body.maxFloors = maxFloors;
      if (minGrowth > 0)          body.minGrowth = minGrowth;
      if (filtersFormState.poiFilters?.length) {
        body.poiFilters = filtersFormState.poiFilters.map((f) => ({
          poiTypeId: f.poiTypeId,
          maxDistanceMeters: f.maxDistanceMeters,
        }));
      }

      try {
        const res = await fetch('http://localhost:4000/heatmap', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        const resAsJson = await res.json();

        const features = resAsJson?.features ?? [];
        if (!features.length) {
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

  const onFinish = (values: FormState) => {
    setFiltersFormState(values);
    setHasSubmitted(true);
  };

  const handleApplySavedSearch = (filters: SearchFilters) => {
    setAppliedValues({ ...filters });
    setFiltersFormState({ ...filters });
    setHasSubmitted(true);
  };

  const handleOpenProperty = (propertyId: number) => {
    navigate(propertyDetailsUrl(propertyId, selectedHexId !== null));
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
              hexId: selectedHexId,
              areaName: selectedAreaName,
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
                            isActive={activeTab === 'map'}
                            onAreaClick={(h3Index, areaName) => {
                              setSelectedHexId(h3Index);
                              setSelectedAreaName(areaName);
                            }}
                          />
                        </div>
                      </Card>
                      <PolygonPropertiesPanel
                        hexId={selectedHexId}
                        areaName={selectedAreaName}
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
                    onClearSelectedProperty={() => setSelectedPropertyId(null)}
                    onOpenProperty={handleOpenProperty}
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
