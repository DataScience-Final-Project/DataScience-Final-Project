import FiltersForm from './components/FiltersForm'
import { message } from 'antd';
import './App.css';

const App = () => {
  const onFinish = (values: any) => {
    console.log('Form submitted with values:', values);
    message.success(`Form submitted! Slider 1: ${values.slider}, Slider 2: ${values.slider2}`);
  };

  return (
    <div className="app-container">
      <FiltersForm onFinish={onFinish} />
    </div>
  )
}

export default App