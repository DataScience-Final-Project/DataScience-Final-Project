import React from 'react';
import { Button, Divider, Form, Segmented, Slider } from 'antd';
import AreaSearchBar from './AreaSearchBar';
import styles from './FiltersForm.module.css';

type FiltersFormProps = {
  onFinish: (values: any) => void
  onAreaSearch: (query: string) => void
}

const formatPriceSliderValue = (value?: number): string => {
  if (value === undefined) return '';
  if (value >= 1_000_000) return '$1,000,000+';
  return `$${value.toLocaleString('en-US')}`;
};

const priceRangeMarks = {
  0: '$0',
  1_000_000: '$1M+',
};

const FiltersForm: React.FC<FiltersFormProps> = ({ onFinish, onAreaSearch }) => {
  const [form] = Form.useForm();


  return (
    <>
      <AreaSearchBar onSearch={onAreaSearch} />

    <Form
      form={form}
      layout="vertical"
      onFinish={onFinish}
      className={styles.form}
      initialValues={{ yearsForward: '1' }}
    >
      <Form.Item label="Price" name="slider">
        <Slider
          range={{ draggableTrack: true }}
          min={0}
          max={1000000}
          step={100000}
          defaultValue={[0, 1000000]}
          marks={priceRangeMarks}
          tooltip={{ formatter: formatPriceSliderValue }}
        />
      </Form.Item>

      <Divider />

      <Form.Item label="Years Forward" name="yearsForward">
        <Segmented
          block
          options={['1', '2', '3', '4', '5', '6+']}
        />
      </Form.Item>

      <Divider />

      <Form.Item>
        <Button type="text" htmlType="submit" className={styles.submitButton}>
          Submit
        </Button>
      </Form.Item>
      
    </Form>
    </>
  );
};

export default FiltersForm;