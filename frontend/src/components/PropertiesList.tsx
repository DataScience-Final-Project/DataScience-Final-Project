import React from 'react';
import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

export type PropertyRow = {
  propertyId: number;
  cityName: string;
  street: string;
  houseNumber: string;
  numRooms: number;
  buildingYear: number;
  propertyType: string;
  floorNumber: number;
  price: number;
};

type Props = {
  areaName: string;
  properties: PropertyRow[];
  loading: boolean;
};

const columns: ColumnsType<PropertyRow> = [
  {
    title: 'Address',
    key: 'address',
    render: (_, r) => `${r.street} ${r.houseNumber}, ${r.cityName}`,
  },
  {
    title: 'Type',
    dataIndex: 'propertyType',
    key: 'propertyType',
    render: (v) => v ? <Tag>{v}</Tag> : '—',
  },
  {
    title: 'Rooms',
    dataIndex: 'numRooms',
    key: 'numRooms',
    render: (v) => v ?? '—',
  },
  {
    title: 'Floor',
    dataIndex: 'floorNumber',
    key: 'floorNumber',
    render: (v) => v ?? '—',
  },
  {
    title: 'Built',
    dataIndex: 'buildingYear',
    key: 'buildingYear',
    render: (v) => v ?? '—',
  },
  {
    title: 'Price',
    dataIndex: 'price',
    key: 'price',
    render: (v: number) =>
      v != null ? `₪${v.toLocaleString('he-IL')}` : '—',
    sorter: (a, b) => (a.price ?? 0) - (b.price ?? 0),
  },
];

const PropertiesList: React.FC<Props> = ({ areaName, properties, loading }) => {
  return (
    <div className="properties-list">
      <h3 className="properties-list__title">
        Properties in <span>{areaName}</span>
        <span className="properties-list__count">{properties.length} listings</span>
      </h3>
      <Table<PropertyRow>
        columns={columns}
        dataSource={properties}
        rowKey="propertyId"
        loading={loading}
        size="small"
        pagination={{ pageSize: 10, showSizeChanger: false }}
        scroll={{ x: true }}
      />
    </div>
  );
};

export default PropertiesList;
