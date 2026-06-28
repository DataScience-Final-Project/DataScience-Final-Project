import { Button, Empty, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useEffect, useState } from 'react';

type HexProperty = {
  propertyId: number;
  cityName: string;
  street: string;
  houseNumber: string;
  numRooms: number | null;
  buildingYear: number | null;
  floorNumber: number | null;
  buildingFloors: number | null;
  assetType: string | null;
  percentChange: number;
  price: number;
};

type Props = {
  hexId: string | null;
  areaName: string | null;
  onOpenProperty: (propertyId: number) => void;
};

function propertyAddress(p: HexProperty) {
  return [p.street, p.houseNumber, p.cityName].filter(Boolean).join(', ') || 'Address unavailable';
}

const formatPrice = (value: number | null) =>
  value === null ? '—' : new Intl.NumberFormat('en-US').format(value);

const PolygonPropertiesPanel = ({ hexId, areaName, onOpenProperty }: Props) => {
  const [properties, setProperties] = useState<HexProperty[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!hexId) {
      setProperties([]);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    fetch(`http://localhost:4000/heatmap/${hexId}/properties`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
      signal: controller.signal,
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Request failed (${r.status})`);
        return r.json();
      })
      .then((data) => {
        if (!controller.signal.aborted) {
          setProperties(Array.isArray(data) ? data : []);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Could not load properties.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [hexId]);

  const columns: ColumnsType<HexProperty> = [
    {
      title: 'Address',
      key: 'address',
      render: (_, p) => propertyAddress(p),
    },
    {
      title: 'Rooms',
      dataIndex: 'numRooms',
      width: 82,
      render: (v: number | null) => v ?? '—',
    },
    {
      title: 'Floor',
      dataIndex: 'floorNumber',
      width: 82,
      render: (v: number | null) => v ?? '—',
    },
    {
      title: 'Predicted growth',
      dataIndex: 'percentChange',
      width: 150,
      render: (v: number) => `${v.toFixed(1)}%`,
    },
    {
      title: 'Price',
      dataIndex: 'price',
      width: 132,
      render: formatPrice,
    },
    {
      title: '',
      key: 'open',
      width: 100,
      render: (_, p) => (
        <Button type="link" onClick={() => onOpenProperty(p.propertyId)}>Open</Button>
      ),
    },
  ];

  return (
    <section className="polygon-properties" aria-live="polite">
      <div className="polygon-properties__heading">
        <div>
          <span className="section-kicker">Selected area</span>
          <h2>{areaName || 'Select an area on the map'}</h2>
        </div>
        {hexId && <Tag color="purple">{properties.length} properties</Tag>}
      </div>

      {!hexId && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Click a hex cell to see its properties."
        />
      )}
      {hexId && error && <div className="properties-error">{error}</div>}
      {hexId && !error && (
        <Table<HexProperty>
          className="property-table property-table--polygon"
          columns={columns}
          dataSource={properties}
          loading={loading}
          rowKey="propertyId"
          pagination={false}
          size="small"
          locale={{ emptyText: 'No properties found in this area.' }}
        />
      )}
    </section>
  );
};

export default PolygonPropertiesPanel;
