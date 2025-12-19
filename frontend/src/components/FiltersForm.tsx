import React from 'react';
import { Button, Form, Slider, message } from 'antd';

type FiltersFormProps = {
  onFinish: (values: any) => void
}

const FiltersForm: React.FC<FiltersFormProps> = ({ onFinish }) => {
  const [form] = Form.useForm();


  return (
    <Form
      form={form}
      labelCol={{ span: 4 }}
      wrapperCol={{ span: 14 }}
      layout="vertical"
      style={{ maxWidth: 600 }}
      onFinish={onFinish}
    >
      <Form.Item label="Slider" name="slider">
        <Slider />
      </Form.Item>

      <Form.Item label="Slider 2" name="slider2">
        <Slider />
      </Form.Item>

      <Form.Item>
        <Button type="primary" htmlType="submit">
          Submit
        </Button>
      </Form.Item>
      
    </Form>
  );
};

export default FiltersForm;