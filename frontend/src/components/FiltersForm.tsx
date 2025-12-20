import React from 'react';
import { Button, Divider, Form, Slider } from 'antd';

type FiltersFormProps = {
  onFinish: (values: any) => void
}

const FiltersForm: React.FC<FiltersFormProps> = ({ onFinish }) => {
  const [form] = Form.useForm();


  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={onFinish}
      style={{ width: '100%' }}
    >
      <Form.Item label="Price" name="slider">
        <Slider range={{ draggableTrack: true }} defaultValue={[0, 1000000]} max={1000000} min={0} />
      </Form.Item>

      <Divider />

      <Form.Item label="Years Forward" name="slider2">
        <Slider range={{ draggableTrack: true }} defaultValue={[1, 10]} max={10} min={1} />
      </Form.Item>

      <Divider />

      <Form.Item>
        <Button type="text" htmlType="submit" className="submit-button" style={{ backgroundColor: '#4e7d96', border:'none', color:'white' }}>
          Submit
        </Button>
      </Form.Item>
      
    </Form>
  );
};

export default FiltersForm;