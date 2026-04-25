import { useCallback, useEffect, useState } from 'react'
import FiltersForm from './components/FiltersForm'
import HeatMap from './components/HeatMap'
import { Card, ConfigProvider, message } from 'antd';
import propCastLogo from './assets/propCastLogo.png';
import './App.css';
import { mockAreas } from './data'
import { dashboardTheme } from './dashboardTheme'
import { normalizeServerData } from './dataTransformers'


const App = () => {
const [filtersFormState, setFiltersFormState] = useState<any>({ yearsForward: 1 })
  const [mapAreas, setMapAreas] = useState(() => mockAreas)
  const [mapFitNonce, setMapFitNonce] = useState(0)
  const [normalizedData, setNormalizedData] = useState<any>(null)

  useEffect(() => {
  const fetchMapArea = async() => {
      // 1. שולפים את השנים מתוך הסטייט של הטופס (אם אין, ברירת המחדל תהיה 1)
      const years = filtersFormState.yearsForward || 1;
      
      // 2. משנים את הכתובת לסטרינג דינמי (Backticks - המירכאות העקומות)
      const res = await fetch(`http://localhost:4000/growth-clusters?years=${years}`);
      const resAsJson = await res.json();
      
      const normalizedData = normalizeServerData(resAsJson);
      setNormalizedData(normalizedData);
      setMapAreas(normalizedData);
  }
  
  fetchMapArea();
  
// 3. הוספנו את הסטייט של הטופס למערך התלויות!
}, [filtersFormState]);

  const onAreaSearch = useCallback((query: string) => {
    const q = query.trim().toLowerCase()
    if (!q) {
      setMapAreas(normalizedData)
      setMapFitNonce((n) => n + 1)
      message.info('Showing all areas')
      return
    }

    const matches = normalizedData.filter((f: any) =>
      String(f.properties?.name ?? '').toLowerCase().includes(q)
    )

    if (!matches.length) {
      message.warning('No matching area or city')
      return
    }

    setMapAreas(matches)
    setMapFitNonce((n) => n + 1)
  }, [normalizedData])


  const onFinish = (values: any) => {
    setFiltersFormState(values);
    console.log('Form submitted with values:', values);
    message.success(`Form submitted! Price: ${values.slider}, Years forward: ${values.yearsForward}`);
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
              <FiltersForm onFinish={onFinish} onAreaSearch={onAreaSearch} />
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

