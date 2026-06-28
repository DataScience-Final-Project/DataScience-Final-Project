import React, { useState, useEffect } from 'react';
import { Button, Divider, Form, InputNumber, Segmented, Slider, Select, message } from 'antd';
import { PlusOutlined, CloseOutlined } from '@ant-design/icons';
import styles from './FiltersForm.module.css';
import type { PoiFilterEntry } from '../api/personalization';

type PoiType = { poiTypeId: number; name: string };

type FiltersFormProps = {
  onFinish: (values: any) => void;
  appliedValues?: any;
}

const formatPriceSliderValue = (value?: number): string => {
  if (value === undefined) return '';
  if (value >= 10_000_000) return '₪10,000,000+';
  return `₪${value.toLocaleString('en-US')}`;
};

const priceRangeMarks = {
  0: '₪0',
  10_000_000: '₪10M+',
};

const FiltersForm: React.FC<FiltersFormProps> = ({ onFinish, appliedValues }) => {
  const [form] = Form.useForm();

  const [poiFilters, setPoiFilters] = useState<PoiFilterEntry[]>([]);
  const [allPoiTypes, setAllPoiTypes] = useState<PoiType[]>([]);
  const [poiSelectValue, setPoiSelectValue] = useState<number | undefined>(undefined);

  // Sync saved search values back into form + POI state
  useEffect(() => {
    if (appliedValues) {
      form.setFieldsValue(appliedValues);
      setPoiFilters(appliedValues.poiFilters ?? []);
    }
  }, [appliedValues, form]);

  // Fetch available POI types from backend
  useEffect(() => {
    fetch('http://localhost:4000/heatmap/poi-types')
      .then((r) => r.json())
      .then((data: unknown) => { if (Array.isArray(data)) setAllPoiTypes(data as PoiType[]); })
      .catch(() => {/* silently ignore — POI section just stays empty */});
  }, []);

  const [citiesList, setCitiesList] = useState<{label: string, value: string}[]>([]);
  const [loadingCities, setLoadingCities] = useState(true);

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
              value: cityName,
            };
          })
          .filter((city: any) => city.label !== 'לא רשום');

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

  const addPoiFilter = (poiTypeId: number) => {
    const type = allPoiTypes.find((t) => t.poiTypeId === poiTypeId);
    if (!type) return;
    setPoiFilters((prev) => [
      ...prev,
      { poiTypeId, name: type.name, maxDistanceMeters: 500 },
    ]);
    setPoiSelectValue(undefined);
  };

  const removePoiFilter = (poiTypeId: number) => {
    setPoiFilters((prev) => prev.filter((f) => f.poiTypeId !== poiTypeId));
  };

  const updatePoiDistance = (poiTypeId: number, maxDistanceMeters: number) => {
    setPoiFilters((prev) =>
      prev.map((f) => f.poiTypeId === poiTypeId ? { ...f, maxDistanceMeters } : f)
    );
  };

  const availablePoiOptions = allPoiTypes
    .filter((t) => !poiFilters.some((f) => f.poiTypeId === t.poiTypeId))
    .map((t) => ({ label: t.name, value: t.poiTypeId }));

  const handleFinish = (values: any) => {
    onFinish({ ...values, poiFilters });
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleFinish}
      className={styles.form}
      initialValues={{ yearsForward: '5', roomsRange: [1, 10], floorsRange: [0, 30], slider: [0, 10000000], minGrowth: 0 }}
    >
      <Form.Item name="city" label="City">
        <Select
          className="city-area-select"
          popupClassName="city-area-select-dropdown"
          showSearch
          allowClear
          loading={loadingCities}
          placeholder="Search for a city..."
          optionFilterProp="label"
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
          max={10000000}
          step={100000}
          defaultValue={[0, 10000000]}
          marks={priceRangeMarks}
          tooltip={{ formatter: formatPriceSliderValue }}
        />
      </Form.Item>

      <Divider />

      <Form.Item label="Rooms" name="roomsRange">
        <Slider
          range={{ draggableTrack: true }}
          min={1}
          max={10}
          step={0.5}
          marks={{ 1: '1', 5: '5', 10: '10+' }}
          tooltip={{ formatter: (v) => `${v} rooms` }}
        />
      </Form.Item>

      <Divider />

      <Form.Item label="Floor" name="floorsRange">
        <Slider
          range={{ draggableTrack: true }}
          min={0}
          max={30}
          step={1}
          marks={{ 0: '0', 10: '10', 20: '20', 30: '30+' }}
          tooltip={{ formatter: (v) => `Floor ${v}` }}
        />
      </Form.Item>

      <Divider />

      <Form.Item label="Min. Predicted Growth" name="minGrowth">
        <InputNumber
          min={0}
          step={5}
          suffix="%"
          style={{ width: '100%' }}
        />
      </Form.Item>

      <Divider />

      <Form.Item label="Years Forward" name="yearsForward">
        <Segmented
          block
          options={['5', '10']}
          onChange={() => form.submit()}
        />
      </Form.Item>

      <Divider />

      {/* POI Distance Filters */}
      <Form.Item label="Nearby POIs">
        <div>
          {poiFilters.map((f) => (
            <div key={f.poiTypeId} className={styles.poiRow}>
              <span className={styles.poiName}>{f.name}</span>
              <InputNumber
                className={styles.poiDistance}
                min={50}
                max={50000}
                step={100}
                value={f.maxDistanceMeters}
                suffix="m"
                onChange={(val) => updatePoiDistance(f.poiTypeId, val ?? 500)}
              />
              <Button
                type="text"
                size="small"
                icon={<CloseOutlined />}
                className={styles.poiRemoveBtn}
                onClick={() => removePoiFilter(f.poiTypeId)}
              />
            </div>
          ))}

          <Select
            value={poiSelectValue}
            placeholder={
              <span className={styles.poiAddPlaceholder}>
                <PlusOutlined style={{ marginRight: 6 }} />
                Add POI filter
              </span>
            }
            options={availablePoiOptions}
            onChange={(val) => addPoiFilter(Number(val))}
            disabled={availablePoiOptions.length === 0 && allPoiTypes.length > 0}
            style={{ width: '100%', marginTop: poiFilters.length > 0 ? 8 : 0 }}
            popupMatchSelectWidth={false}
          />
        </div>
      </Form.Item>

      <Divider />

      <Form.Item>
        <Button type="primary" htmlType="submit" className={styles.submitButton} style={{ width: '100%' }}>
          Submit
        </Button>
      </Form.Item>

    </Form>
  );
};

export default FiltersForm;
