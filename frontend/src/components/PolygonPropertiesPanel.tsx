import { Button, Empty, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useEffect, useState } from 'react';
import { fetchProperties, type PropertyListItem } from '../api/properties';

type PolygonPropertiesPanelProps = {
  clusterId: number | null;
  areaName: string | null;
  onOpenProperty: (propertyId: number) => void;
};

function propertyAddress(property: PropertyListItem) {
  return [property.street, property.houseNumber, property.cityName].filter(Boolean).join(', ') || 'Address unavailable';
}

const formatPrice = (value: number | null) => value === null ? '—' : new Intl.NumberFormat('en-US').format(value);

const PolygonPropertiesPanel = ({ clusterId, areaName, onOpenProperty }: PolygonPropertiesPanelProps) => {
  const [properties, setProperties] = useState<PropertyListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!clusterId) {
      return;
    }

    const controller = new AbortController();
    Promise.resolve()
      .then(() => {
        if (controller.signal.aborted) return null;
        setLoading(true);
        setError(null);
        return fetchProperties({ clusterId, pageSize: 10 });
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
  }, [clusterId]);

  const columns: ColumnsType<PropertyListItem> = [
    {
      title: 'Address',
      key: 'address',
      render: (_, property) => propertyAddress(property),
    },
    {
      title: 'Rooms',
      dataIndex: 'numRooms',
      width: 82,
      render: (value: number | null) => value ?? '—',
    },
    {
      title: 'Building floors',
      dataIndex: 'buildingFloors',
      width: 132,
      render: (value: number | null) => value ?? '—',
    },
    {
      title: 'Latest price',
      dataIndex: 'latestSalePrice',
      width: 132,
      render: formatPrice,
    },
    {
      title: '',
      key: 'open',
      width: 100,
      render: (_, property) => (
        <Button type="link" onClick={() => onOpenProperty(property.propertyId)}>
          Open
        </Button>
      ),
    },
  ];

  return (
    <section className="polygon-properties" aria-live="polite">
      <div className="polygon-properties__heading">
        <div>
          <span className="section-kicker">Selected polygon</span>
          <h2>{areaName || 'Select a polygon on the map'}</h2>
        </div>
        {clusterId && <Tag color="purple">{total.toLocaleString()} properties</Tag>}
      </div>

      {!clusterId && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Click a polygon to see its properties." />}
      {clusterId && error && <div className="properties-error">{error}</div>}
      {clusterId && !error && (
        <Table<PropertyListItem>
          className="property-table property-table--polygon"
          columns={columns}
          dataSource={properties}
          loading={loading}
          rowKey="propertyId"
          pagination={false}
          size="small"
          locale={{ emptyText: 'No mapped properties were found in this polygon.' }}
        />
      )}
    </section>
  );
};

export default PolygonPropertiesPanel;
