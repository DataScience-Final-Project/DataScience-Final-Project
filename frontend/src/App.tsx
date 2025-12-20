import React, { useState } from 'react'
import FiltersForm from './components/FiltersForm'
import HeatMap from './components/HeatMap'
import { ConfigProvider, message } from 'antd';
import propCastLogo from './assets/propCastLogo.png';
import './App.css';

const App = () => {
  const [filtersFormState, setFiltersFormState] = useState<any>({})

  const onFinish = (values: any) => {
    console.log('Form submitted with values:', values);
    message.success(`Form submitted! Slider 1: ${values.slider}, Slider 2: ${values.slider2}`);
  };

  return (
    <ConfigProvider theme={{
      components: {
        Slider: {
          trackBg: '#4e7d96',
          handleColor: '#ff844b',
          handleActiveColor:'#ff844b',
          dotActiveBorderColor:'#ff844b',
          trackHoverBg:'#ff844b',
          handleActiveOutlineColor:'rgba(255, 222, 207, 0.55)',
        },
      },
    }}>
    <div className="app-container">

      <div className="header-container">
        <img src={propCastLogo} alt="PropCast" />
      </div>

      <div className="content-container">

        <div className="form-container">
          <FiltersForm onFinish={onFinish} />
        </div>

        <div className="map-container">
        <HeatMap filters={filtersFormState} />
        </div>

      </div>

    </div>
    </ConfigProvider>

  )
}

export default App