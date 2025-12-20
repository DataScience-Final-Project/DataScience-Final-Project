import React, { useState } from 'react'
import FiltersForm from './components/FiltersForm'
import { ConfigProvider, message } from 'antd';
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
        },
      },
    }}>
    <div className="app-container">

      <div className="header-container">PropCast</div>

      <div className="content-container">

        <div className="form-container">
          <FiltersForm onFinish={onFinish} />
        </div>

        <div className="map-container">map</div>

      </div>

    </div>
    </ConfigProvider>

  )
}

export default App