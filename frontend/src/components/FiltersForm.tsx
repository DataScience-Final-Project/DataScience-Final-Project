import React, { useState, useEffect } from 'react';
import { Button, Divider, Form, Segmented, Slider, Select, message } from 'antd';
import styles from './FiltersForm.module.css';

// הסרנו את onAreaSearch כי עכשיו החיפוש הוא חלק מהטופס ונשלח ב-onFinish
type FiltersFormProps = {
  onFinish: (values: any) => void;
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

const FiltersForm: React.FC<FiltersFormProps> = ({ onFinish }) => {
  const [form] = Form.useForm();
  
  // States עבור חיפוש הערים
  const [citiesList, setCitiesList] = useState<{label: string, value: string}[]>([]);
  const [loadingCities, setLoadingCities] = useState(true);

  // משיכת הערים מה-API של gov.il כשהקומפוננטה עולה
  useEffect(() => {
    const fetchIsraelCities = async () => {
      try {
        const response = await fetch(
          'https://data.gov.il/api/3/action/datastore_search?resource_id=5c78e9fa-c2e2-4771-93ff-7f400a12f7ba&limit=1500'
        );
        const data = await response.json();
        
        const records = data.result.records;

        const formattedCities = records
          .map((record: any) => {
            const cityName = record['שם_ישוב'].trim();
            return {
              label: cityName,
              value: cityName, // ה-value שיישלח לשרת שלכם
            };
          })
          .filter((city: any) => city.label !== 'לא רשום');

        // מיון אלפביתי של הערים שיהיה נוח
        formattedCities.sort((a: any, b: any) => a.label.localeCompare(b.label, 'he'));

        setCitiesList(formattedCities);
      } catch (error) {
        console.error('Error fetching cities:', error);
        message.error('שגיאה בטעינת רשימת הערים');
      } finally {
        setLoadingCities(false);
      }
    };

    fetchIsraelCities();
  }, []);

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={onFinish}
      className={styles.form}
      initialValues={{ yearsForward: '1' }}
    >
      {/* שורת חיפוש העיר */}
      <Form.Item name="city" label="City / Area">
        <Select
          showSearch
          allowClear
          loading={loadingCities}
          placeholder="Search for a city..."
          optionFilterProp="label"
          // מאפשר חיפוש תקין גם באמצע המילה
          filterOption={(input, option) =>
            (option?.label ?? '').includes(input)
          }
          options={citiesList}
        />
      </Form.Item>

      <Divider />

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
        {/* שיניתי טיפה את העיצוב לכפתור בולט יותר כדי שיהיה ברור שזה כפתור חיפוש/שמירה */}
        <Button type="primary" htmlType="submit" className={styles.submitButton} style={{ width: '100%' }}>
          Search / Submit
        </Button>
      </Form.Item>
      
    </Form>
  );
};

export default FiltersForm;