import { useEffect, useState } from 'react';
import FiltersForm from './components/FiltersForm';
import HeatMap from './components/HeatMap';
import { Card, ConfigProvider, message } from 'antd';
import propCastLogo from './assets/propCastLogo.png';
import './App.css';
import { dashboardTheme } from './dashboardTheme';
import { normalizeServerData } from './dataTransformers';

const App = () => {
  // הגדרת ערך התחלתי לטופס (שנה 1 קדימה)
  const [filtersFormState, setFiltersFormState] = useState<any>({ yearsForward: '1' });
  const [mapAreas, setMapAreas] = useState<any[]>([]); // מתחיל כמערך ריק כי אנחנו מביאים מהשרת
  const [mapFitNonce, setMapFitNonce] = useState(0);

  useEffect(() => {
    const fetchMapArea = async () => {
      // 1. שולפים את הנתונים מהטופס (מנקים את פלוס מ-'6+' כדי שהשרת יקבל רק מספר)
      const years = filtersFormState.yearsForward?.replace('+', '') || '1';
      
      // 2. בונים את ה-URL הבסיסי
      let url = `http://possible-condiment-debate.ngrok-free.dev/growth-clusters?years=${years}`;

      // מוסיפים עיר אם המשתמש בחר בטופס
      if (filtersFormState.city) {
        // encodeURIComponent חשוב כדי שדפדפנים ידעו לקרוא אותיות בעברית ורווחים בתוך הלינק
        url += `&city=${encodeURIComponent(filtersFormState.city)}`;
      }

      // מוסיפים את טווח המחירים מהסליידר (מינימום ומקסימום)
      if (filtersFormState.slider && filtersFormState.slider.length === 2) {
        url += `&minPrice=${filtersFormState.slider[0]}&maxPrice=${filtersFormState.slider[1]}`;
      }

      console.log('Sending request to URL:', url); // כדי שתוכלי לראות בלוג איזה לינק נשלח

      try {
        // הוספת ההדר פה מונעת מ-ngrok להחזיר דף אזהרה במקום את הנתונים
        const res = await fetch(url, {
          headers: {
            'ngrok-skip-browser-warning': 'true'
          }
        });
        
        const resAsJson = await res.json();

        // 3. מה קורה אם השרת מחזיר מערך ריק (אין נתונים לחיפוש הזה)?
        if (!resAsJson || resAsJson.length === 0) {
          message.warning('לא נמצאו אזורי השקעה שמתאימים לסינון. נסה לשנות אזור או תקציב.');
          setMapAreas([]); // מנקים את המפה
          setMapFitNonce((n) => n + 1); // מרפרשים את המפה
          return;
        }

        // 4. אם יש נתונים, מנרמלים ומציגים אותם
        const normalizedData = normalizeServerData(resAsJson);
        setMapAreas(normalizedData);
        setMapFitNonce((n) => n + 1); // עושה זום אוטומטי לאזורים החדשים

      } catch (error) {
        console.error('Fetch error:', error);
        message.error('שגיאה בתקשורת מול השרת. ודא שהשרת רץ.');
      }
    };

    fetchMapArea();
  }, [filtersFormState]); // ה-useEffect הזה ירוץ מחדש בכל פעם ש-filtersFormState משתנה

  // פונקציה שמופעלת כשהמשתמש לוחץ "Submit" בטופס
  const onFinish = (values: any) => {
    setFiltersFormState(values);
    console.log('Form submitted with values:', values);
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
            <Card className="dashboard-card dashboard-card--filters" bordered={false} title="Filters">
              <FiltersForm onFinish={onFinish} />
            </Card>

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

export default App