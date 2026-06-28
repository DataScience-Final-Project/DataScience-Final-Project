import { Button, Empty, Input, InputNumber, Select, Space, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { useDeferredValue, useEffect, useMemo, useState } from 'react';
import {
  fetchPropertyFilterOptions,
  fetchProperties,
  type PoiSource,
  type PropertyFilterOptions,
  type PropertyFilters,
} from '../api/properties';

type PropertiesTabProps = {
  selectedPropertyId: number | null;
  onClearSelectedProperty: () => void;
  onOpenProperty: (propertyId: number) => void;
};

const EMPTY_FILTERS: PropertyFilters = { poiSource: 'both' };

function propertyAddress(property: PropertyListItem) {
  return [property.street, property.houseNumber, property.cityName].filter(Boolean).join(', ') || 'Address unavailable';
}

function formatNumber(value: number | null | undefined) {
  return value === null || value === undefined ? '—' : new Intl.NumberFormat('en-US').format(value);
}

function formatDate(value: string | null) {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleDateString();
}

const PropertiesTab = ({
  selectedPropertyId,
  onClearSelectedProperty,
  onOpenProperty,
}: PropertiesTabProps) => {
  const [filters, setFilters] = useState<PropertyFilters>(EMPTY_FILTERS);
  const [search, setSearch] = useState('');
  const deferredSearch = useDeferredValue(search);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [properties, setProperties] = useState<PropertyListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<PropertyFilterOptions>({ cities: [], propertyTypes: [], poiTypes: [] });

  const activeFilters = useMemo(() => ({
    ...filters,
    search: deferredSearch,
    propertyId: selectedPropertyId,
    page,
    pageSize,
  }), [deferredSearch, filters, page, pageSize, selectedPropertyId]);

  useEffect(() => {
    fetchPropertyFilterOptions().then(setOptions).catch(() => {
      // The table remains usable when options cannot be preloaded.
    });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    Promise.resolve()
      .then(() => {
        if (controller.signal.aborted) return null;
        setLoading(true);
        setError(null);
        return fetchProperties(activeFilters);
      })
      .then((result) => {
        if (controller.signal.aborted || !result) return;
        setProperties(result.items);
        setTotal(result.total);
      })
      .catch((requestError) => {
        if (controller.signal.aborted) return;
        setError(requestError instanceof Error ? requestError.message : 'Could not load properties.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [activeFilters]);

  const updateFilter = <K extends keyof PropertyFilters>(key: K, value: PropertyFilters[K]) => {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const resetFilters = () => {
    setSearch('');
    setFilters(EMPTY_FILTERS);
    setPage(1);
  };

  const columns: ColumnsType<PropertyListItem> = [
    { title: 'ID', dataIndex: 'propertyId', width: 92 },
    {
      title: 'Address',
      key: 'address',
      render: (_, property) => (
        <button className="property-link" type="button" onClick={() => onOpenProperty(property.propertyId)}>
          {propertyAddress(property)}
        </button>
      ),
    },
    { title: 'Rooms', dataIndex: 'numRooms', width: 82, render: formatNumber },
    { title: 'Year', dataIndex: 'buildingYear', width: 82, render: formatNumber },
    { title: 'Building floors', dataIndex: 'buildingFloors', width: 132, render: formatNumber },
    { title: 'Type', dataIndex: 'propertyType', width: 78, render: formatNumber },
    { title: 'Latest price', dataIndex: 'latestSalePrice', width: 130, render: formatNumber },
    { title: 'Sale date', dataIndex: 'latestSaleDate', width: 116, render: formatDate },
  ];

  return (
    <section className="properties-workspace">
      <div className="properties-workspace__intro">
        <div>
          <span className="section-kicker">Database explorer</span>
          <h1>Properties</h1>
          <p>Search every stored property field and narrow results by nearby current or future points of interest.</p>
        </div>
        <Space wrap>
          {selectedPropertyId && (
            <>
              <Tag color="blue">Selected property #{selectedPropertyId}</Tag>
              <Button onClick={onClearSelectedProperty}>Show all</Button>
            </>
          )}
        </Space>
      </div>

      <div className="properties-filters">
        <Input
          className="properties-filters__search"
          allowClear
          prefix={<SearchOutlined />}
          placeholder="Search ID, address, price, details, or any saved metric"
          value={search}
          onChange={(event) => {
            setPage(1);
            setSearch(event.target.value);
          }}
        />
        <Select
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder="City"
          value={filters.city}
          onChange={(value) => updateFilter('city', value)}
          options={options.cities.map(({ cityName }) => ({ value: cityName, label: cityName }))}
        />
        <Select
          allowClear
          placeholder="Property type"
          value={filters.propertyType}
          onChange={(value) => updateFilter('propertyType', value)}
          options={options.propertyTypes.map(({ propertyType }) => ({ value: propertyType, label: `Type ${propertyType}` }))}
        />
        <InputNumber placeholder="Min rooms" min={0} value={filters.minRooms ?? undefined} onChange={(value) => updateFilter('minRooms', value)} />
        <InputNumber placeholder="Max rooms" min={0} value={filters.maxRooms ?? undefined} onChange={(value) => updateFilter('maxRooms', value)} />
        <InputNumber placeholder="Min floors" min={0} value={filters.minBuildingFloors ?? undefined} onChange={(value) => updateFilter('minBuildingFloors', value)} />
        <InputNumber placeholder="Max floors" min={0} value={filters.maxBuildingFloors ?? undefined} onChange={(value) => updateFilter('maxBuildingFloors', value)} />
        <InputNumber placeholder="Built after" min={0} value={filters.minBuildingYear ?? undefined} onChange={(value) => updateFilter('minBuildingYear', value)} />
        <InputNumber placeholder="Built before" min={0} value={filters.maxBuildingYear ?? undefined} onChange={(value) => updateFilter('maxBuildingYear', value)} />
        <InputNumber placeholder="Min latest price" min={0} value={filters.minPrice ?? undefined} onChange={(value) => updateFilter('minPrice', value)} />
        <InputNumber placeholder="Max latest price" min={0} value={filters.maxPrice ?? undefined} onChange={(value) => updateFilter('maxPrice', value)} />
        <Select
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder="Nearby POI type"
          value={filters.poiTypeId}
          onChange={(value) => updateFilter('poiTypeId', value)}
          options={options.poiTypes.map((poi) => ({ value: poi.id, label: poi.name }))}
        />
        <Select<PoiSource>
          value={filters.poiSource ?? 'both'}
          onChange={(value) => updateFilter('poiSource', value)}
          options={[
            { value: 'both', label: 'Current + future POIs' },
            { value: 'current', label: 'Current POIs only' },
            { value: 'future', label: 'Future POIs only' },
          ]}
        />
        <InputNumber
          placeholder="POI distance (m)"
          min={1}
          disabled={!filters.poiTypeId}
          value={filters.poiDistanceMeters ?? undefined}
          onChange={(value) => updateFilter('poiDistanceMeters', value)}
        />
        <Button icon={<ReloadOutlined />} onClick={resetFilters}>Reset filters</Button>
      </div>

      {error && <div className="properties-error">{error}</div>}
      {!error && (
        <Table<PropertyListItem>
          className="property-table property-table--all"
          columns={columns}
          dataSource={properties}
          loading={loading}
          rowKey="propertyId"
          scroll={{ x: 1080 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (count) => `${count.toLocaleString()} properties`,
            onChange: (nextPage, nextPageSize) => {
              setPage(nextPage);
              setPageSize(nextPageSize);
            },
          }}
          locale={{ emptyText: <Empty description="No properties match the current filters." /> }}
        />
      )}

    </section>
  );
};

export default PropertiesTab;
