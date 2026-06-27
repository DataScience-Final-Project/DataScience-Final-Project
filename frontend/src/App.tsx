import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import FiltersForm from './components/FiltersForm';
import HeatMap from './components/HeatMap';
import PropertiesList from './components/PropertiesList';
import type { PropertyRow } from './components/PropertiesList';
import SavedSearches from './components/SavedSearches';
import { Button, Card, ConfigProvider, message } from 'antd';
import { LogoutOutlined } from '@ant-design/icons';
import propCastLogo from './assets/propCastLogo.png';
import './App.css';
import { dashboardTheme } from './dashboardTheme';
import { normalizeServerData } from './dataTransformers';
import type { SearchFilters } from './api/personalization';
import { getCurrentUser, clearCurrentUser } from './api/auth';

const App = () => {
  const navigate = useNavigate();
  const currentUser = getCurrentUser();

  const handleLogout = () => {
    clearCurrentUser();
    navigate('/');
  };
  const [filtersFormState, setFiltersFormState] = useState<any>({ yearsForward: '1' });
  const [mapAreas, setMapAreas] = useState<any[]>([]);
  const [mapFitNonce, setMapFitNonce] = useState(0);
  // ערכים שנדחפים בחזרה לטופס כשמחילים חיפוש שמור
  const [appliedValues, setAppliedValues] = useState<any>(null);
  // האם המשתמש כבר שלח את הטופס לפחות פעם אחת (שולט בכפתור השמירה)
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const isInitialFetchRef = useRef(true);

  const [selectedArea, setSelectedArea] = useState<{ h3Index: string; displayName: string } | null>(null);
  const [areaProperties, setAreaProperties] = useState<PropertyRow[]>([]);
  const [propertiesLoading, setPropertiesLoading] = useState(false);

  useEffect(() => {
    const fetchMapArea = async () => {
      const years = filtersFormState.yearsForward?.replace('+', '') || '5';
      const [minPrice, maxPrice]: [number, number] = filtersFormState.slider ?? [0, 10_000_000];
      const [minRooms, maxRooms]: [number, number] = filtersFormState.roomsRange ?? [1, 10];
      const [minFloors, maxFloors]: [number, number] = filtersFormState.floorsRange ?? [0, 30];
      const minGrowth: number = filtersFormState.minGrowth ?? 0;

      const body: Record<string, any> = { years: Number(years) };
      if (filtersFormState.city) body.city = filtersFormState.city;
      if (minPrice > 0)          body.minPrice = minPrice;
      if (maxPrice < 10_000_000) body.maxPrice = maxPrice;
      if (minRooms > 1)          body.minRooms = minRooms;
      if (maxRooms < 10)         body.maxRooms = maxRooms;
      if (minFloors > 0)         body.minFloors = minFloors;
      if (maxFloors < 30)        body.maxFloors = maxFloors;
      if (minGrowth > 0)         body.minGrowth = minGrowth;

      console.log('POST /heatmap', body);

      try {
        const res = await fetch('http://localhost:4000/heatmap', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const resAsJson = await res.json();
        console.log('DATA FROM SERVER:', resAsJson);

        const features = resAsJson?.features ?? [];
        if (!features.length) {
          message.warning('לא נמצאו אזורי השקעה שמתאימים לסינון. נסה לשנות אזור או תקציב.');
          setMapAreas([]);
          if (!isInitialFetchRef.current) setMapFitNonce((n) => n + 1);
          return;
        }

        const normalizedData = normalizeServerData(resAsJson, years);
        setMapAreas(normalizedData);
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
    if (!selectedArea) return;
    setPropertiesLoading(true);
    const years = filtersFormState.yearsForward?.replace('+', '') || '5';
    fetch(`http://localhost:4000/heatmap/${selectedArea.h3Index}/properties?years=${years}`)
      .then((r) => r.json())
      .then((data) => setAreaProperties(data))
      .catch(() => message.error('Failed to load properties for this area.'))
      .finally(() => setPropertiesLoading(false));
  }, [selectedArea, filtersFormState.yearsForward]);

  const handleAreaClick = (h3Index: string, displayName: string) => {
    setSelectedArea({ h3Index, displayName });
    setAreaProperties([]);
  };

  const onFinish = (values: any) => {
    setFiltersFormState(values);
    setHasSubmitted(true);
    console.log('Form submitted with values:', values);
  };

  // הפעלת חיפוש שמור: דוחפים את הערכים לטופס וגם מרעננים את המפה
  const handleApplySavedSearch = (filters: SearchFilters) => {
    const values = { ...filters };
    setAppliedValues(values);
    setFiltersFormState(values);
    setHasSubmitted(true);
  };

  // הפילטרים הנוכחיים שיישמרו בלחיצה על "Save search"
  const currentFilters: SearchFilters = {
    city: filtersFormState.city,
    slider: filtersFormState.slider,
    yearsForward: filtersFormState.yearsForward,
    roomsRange: filtersFormState.roomsRange,
    floorsRange: filtersFormState.floorsRange,
    minGrowth: filtersFormState.minGrowth,
  };

  return (
    <ConfigProvider theme={dashboardTheme}>
      <div className="app-shell">
        <header className="dashboard-header">
          {currentUser && (
            <div className="dashboard-welcome">
              Welcome, {currentUser.firstName}
            </div>
          )}
          <div className="dashboard-brand">
            <img src={propCastLogo} alt="PropCast" />
          </div>
          <Button
            className="dashboard-logout"
            icon={<LogoutOutlined />}
            onClick={handleLogout}
          >
            Log out
          </Button>
        </header>

        <main className="dashboard-main">
          <div className="dashboard-grid">
            <div className="dashboard-left-col">
              <Card className="dashboard-card dashboard-card--filters" bordered={false} title="Filters">
                <FiltersForm onFinish={onFinish} appliedValues={appliedValues} />
              </Card>

              <Card
                className="dashboard-card dashboard-card--saved"
                bordered={false}
                title="Saved searches"
              >
                <SavedSearches
                  currentFilters={currentFilters}
                  canSave={hasSubmitted}
                  onApply={handleApplySavedSearch}
                />
              </Card>
            </div>

            <Card className="dashboard-card dashboard-card--map" bordered={false} title="Market map">
              <div className="heatmap-shell">
                <HeatMap areas={mapAreas} fitBoundsNonce={mapFitNonce} onAreaClick={handleAreaClick} />
              </div>
            </Card>
          </div>

          {selectedArea && (
            <Card
              className="dashboard-card dashboard-card--properties"
              bordered={false}
              title={null}
            >
              <PropertiesList
                areaName={selectedArea.displayName}
                properties={areaProperties}
                loading={propertiesLoading}
              />
            </Card>
          )}
        </main>
      </div>
    </ConfigProvider>
  )
}

export default App;