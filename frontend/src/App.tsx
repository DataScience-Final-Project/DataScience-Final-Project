import { useEffect, useRef, useState } from 'react';
import FiltersForm from './components/FiltersForm';
import HeatMap from './components/HeatMap';
import SavedSearches from './components/SavedSearches';
import { Card, ConfigProvider, message } from 'antd';
import propCastLogo from './assets/propCastLogo.png';
import './App.css';
import { dashboardTheme } from './dashboardTheme';
import { normalizeServerData } from './dataTransformers';
import type { SearchFilters } from './api/personalization';

const App = () => {
  const [filtersFormState, setFiltersFormState] = useState<any>({ yearsForward: '1' });
  const [mapAreas, setMapAreas] = useState<any[]>([]);
  const [mapFitNonce, setMapFitNonce] = useState(0);
  // ערכים שנדחפים בחזרה לטופס כשמחילים חיפוש שמור
  const [appliedValues, setAppliedValues] = useState<any>(null);
  // האם המשתמש כבר שלח את הטופס לפחות פעם אחת (שולט בכפתור השמירה)
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const isInitialFetchRef = useRef(true);

  useEffect(() => {
    const fetchMapArea = async () => {
      
      // 1. חילוץ הנתונים מהטופס
      const years = filtersFormState.yearsForward?.replace('+', '') || '1';
      
      // 2. בניית הלינק לשרת
      let url = `http://localhost:4000/growth-clusters?years=${years}`;

      if (filtersFormState.city) {
        url += `&city=${encodeURIComponent(filtersFormState.city)}`;
      }
      if (filtersFormState.slider && filtersFormState.slider.length === 2) {
        url += `&minPrice=${filtersFormState.slider[0]}&maxPrice=${filtersFormState.slider[1]}`;
      }

      console.log('Sending real request to URL:', url);

      try {
        // 3. שליחת הבקשה לשרת האמיתי
        const res = await fetch(url);
        const resAsJson = await res.json();
        console.log("DATA FROM SERVER:", resAsJson);
        // 4. טיפול במצב שבו אין תוצאות
        if (!resAsJson || resAsJson.length === 0) {
          message.warning('לא נמצאו אזורי השקעה שמתאימים לסינון. נסה לשנות אזור או תקציב.');
          setMapAreas([]);
          if (!isInitialFetchRef.current) {
            setMapFitNonce((n) => n + 1);
          }
          return;
        }

        // 5. נירמול הנתונים והצגתם על המפה
        const normalizedData = normalizeServerData(resAsJson, years);
        setMapAreas(normalizedData);
        if (!isInitialFetchRef.current) {
          setMapFitNonce((n) => n + 1);
        }

      } catch (error) {
        console.error('Fetch error:', error);
        message.error('שגיאה בתקשורת מול השרת. ודאי שהשרת רץ.');
      } finally {
        isInitialFetchRef.current = false;
      }
    };

    fetchMapArea();
  }, [filtersFormState]);

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
  };

  return (
    <ConfigProvider theme={dashboardTheme}>
      <div className="app-shell">
        <header className="dashboard-header">
          <div className="dashboard-brand">
            <img src={propCastLogo} alt="PropCast" />
          </div>
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
                <HeatMap areas={mapAreas} fitBoundsNonce={mapFitNonce} />
              </div>
            </Card>
          </div>
        </main>
      </div>
    </ConfigProvider>
  )
}

export default App;