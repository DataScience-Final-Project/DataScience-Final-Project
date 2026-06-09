import React, { useEffect, useState } from 'react';
import { Button, Empty, Popconfirm, Tag, message } from 'antd';
import {
  DeleteOutlined,
  EnvironmentOutlined,
  PushpinOutlined,
} from '@ant-design/icons';
import {
  createSavedSearch,
  deleteSavedSearch,
  listSavedSearches,
  type SavedSearch,
  type SearchFilters,
} from '../api/personalization';
import styles from './SavedSearches.module.css';

type SavedSearchesProps = {
  // The filters currently applied in the form (last submitted values).
  currentFilters: SearchFilters;
  // Whether the user has submitted the form at least once (controls Save button).
  canSave: boolean;
  // Push a saved search back into the form + map.
  onApply: (filters: SearchFilters) => void;
};

const PRICE_MAX = 10_000_000;

const formatPrice = (value: number): string => {
  if (value >= PRICE_MAX) return '₪10M+';
  return `₪${value.toLocaleString('en-US')}`;
};

const formatPriceRange = (slider?: [number, number]): string | null => {
  if (!slider || slider.length !== 2) return null;
  const [min, max] = slider;
  // A full-range slider isn't a meaningful filter, so skip it.
  if (min <= 0 && max >= PRICE_MAX) return null;
  return `${formatPrice(min)} – ${formatPrice(max)}`;
};

// Build a short human-readable name to store alongside the filters.
const buildSearchName = (filters: SearchFilters): string => {
  const parts: string[] = [];
  if (filters.city) parts.push(filters.city);
  const price = formatPriceRange(filters.slider);
  if (price) parts.push(price);
  if (filters.yearsForward) parts.push(`${filters.yearsForward} years`);
  return parts.length ? parts.join(' · ') : 'All areas';
};

const SavedSearches: React.FC<SavedSearchesProps> = ({
  currentFilters,
  canSave,
  onApply,
}) => {
  const [items, setItems] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    listSavedSearches()
      .then((data) => {
        if (active) setItems(data);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const name = buildSearchName(currentFilters);
      const saved = await createSavedSearch(name, currentFilters);
      setItems((prev) => [saved, ...prev]);
      message.success('Search saved');
    } catch {
      message.error('Could not save the search');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
    try {
      await deleteSavedSearch(id);
    } catch {
      message.error('Could not delete the search');
    }
  };

  return (
    <div className={styles.wrapper}>
      <Button
        type="primary"
        icon={<PushpinOutlined />}
        className={styles.saveButton}
        block
        loading={saving}
        disabled={!canSave}
        onClick={handleSave}
      >
        Save search
      </Button>
      {!canSave && (
        <p className={styles.hint}>Submit the filters to save this search.</p>
      )}

      <div className={styles.list}>
        {loading ? (
          <p className={styles.hint}>Loading…</p>
        ) : items.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={<span className={styles.hint}>No saved searches yet</span>}
          />
        ) : (
          items.map((item) => {
            const price = formatPriceRange(item.filters.slider);
            return (
              <div key={item.id} className={styles.item}>
                <div className={styles.itemHeader}>
                  <span className={styles.itemTitle} dir="ltr">
                    {item.name}
                  </span>
                  <Popconfirm
                    title="Delete this saved search?"
                    okText="Delete"
                    cancelText="Cancel"
                    onConfirm={() => handleDelete(item.id)}
                  >
                    <Button
                      type="text"
                      size="small"
                      className={styles.deleteButton}
                      icon={<DeleteOutlined />}
                    />
                  </Popconfirm>
                </div>

                <div className={styles.tags}>
                  {item.filters.yearsForward && (
                    <Tag className={styles.tag}>
                      {item.filters.yearsForward} years forward
                    </Tag>
                  )}
                  {price && <Tag className={styles.tag}>{price}</Tag>}
                  {item.filters.city && (
                    <Tag className={styles.tag} icon={<EnvironmentOutlined />}>
                      {item.filters.city}
                    </Tag>
                  )}
                  {!item.filters.city && (
                    <Tag className={styles.tag}>All cities</Tag>
                  )}
                </div>

                <Button
                  type="default"
                  size="small"
                  icon={<EnvironmentOutlined />}
                  className={styles.showButton}
                  onClick={() => onApply(item.filters)}
                >
                  Show on map
                </Button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default SavedSearches;
