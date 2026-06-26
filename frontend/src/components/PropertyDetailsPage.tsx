import { AimOutlined, ArrowLeftOutlined, EnvironmentOutlined, HomeOutlined, LinkOutlined } from '@ant-design/icons';
import { Button, ConfigProvider, Tag } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import propCastLogo from '../assets/propCastLogo.png';
import { clearCurrentUser, getCurrentUser } from '../api/auth';
import { fetchPropertyDetails, type NearbyPoi, type PropertyDetails } from '../api/properties';
import { dashboardTheme } from '../dashboardTheme';

function propertyAddress(property: PropertyDetails) {
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

function formatCoordinate(value: number | null) {
  return value === null ? '—' : value.toFixed(6);
}

function formatFeatureLabel(key: string) {
  return key
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatFeatureValue(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  return typeof value === 'number' ? formatNumber(value) : String(value);
}

function openStreetMapEmbedUrl(lat: number, lon: number) {
  const latitudePadding = 0.0025;
  const longitudePadding = 0.0035;
  const bbox = [lon - longitudePadding, lat - latitudePadding, lon + longitudePadding, lat + latitudePadding]
    .map((value) => value.toFixed(6))
    .join('%2C');
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat.toFixed(6)}%2C${lon.toFixed(6)}`;
}

function googleMapsUrl(property: PropertyDetails) {
  const coordinates = property.lat !== null && property.lon !== null
    ? `${property.lat},${property.lon}`
    : propertyAddress(property);
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(coordinates)}`;
}

function yad2SearchUrl(property: PropertyDetails) {
  const searchQuery = propertyAddress(property);
  return `https://www.yad2.co.il/realestate/forsale?propertygroup=apartments&searchText=${encodeURIComponent(searchQuery)}`;
}

function parsePositiveInteger(value: string | null) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function marketMapPolygonUrl(propertyId: number | null, clusterId: number, areaName: string | null) {
  const params = new URLSearchParams({
    tab: 'map',
    clusterId: String(clusterId),
  });

  if (propertyId) params.set('propertyId', String(propertyId));
  if (areaName) params.set('areaName', areaName);

  return `/dashboard?${params.toString()}`;
}

type NearbyPoiGroup = {
  typeId: number;
  typeName: string;
  items: NearbyPoi[];
  currentCount: number;
  futureCount: number;
  nearestDistanceMeters: number;
};

function groupNearbyPois(pois: NearbyPoi[]): NearbyPoiGroup[] {
  const groups = new Map<number, NearbyPoiGroup>();

  for (const poi of pois) {
    const existingGroup = groups.get(poi.typeId);

    if (existingGroup) {
      existingGroup.items.push(poi);
      existingGroup.nearestDistanceMeters = Math.min(existingGroup.nearestDistanceMeters, poi.distanceMeters);
      if (poi.source === 'future') {
        existingGroup.futureCount += 1;
      } else {
        existingGroup.currentCount += 1;
      }
      continue;
    }

    groups.set(poi.typeId, {
      typeId: poi.typeId,
      typeName: poi.typeName,
      items: [poi],
      currentCount: poi.source === 'current' ? 1 : 0,
      futureCount: poi.source === 'future' ? 1 : 0,
      nearestDistanceMeters: poi.distanceMeters,
    });
  }

  return Array.from(groups.values())
    .map((group) => ({
      ...group,
      items: [...group.items].sort((firstPoi, secondPoi) => firstPoi.distanceMeters - secondPoi.distanceMeters),
    }))
    .sort((firstGroup, secondGroup) =>
      firstGroup.nearestDistanceMeters - secondGroup.nearestDistanceMeters ||
      firstGroup.typeName.localeCompare(secondGroup.typeName)
    );
}

const PropertyDetailsPage = () => {
  const navigate = useNavigate();
  const { propertyId: propertyIdParam } = useParams();
  const [searchParams] = useSearchParams();
  const propertyId = Number(propertyIdParam);
  const hasValidPropertyId = Number.isInteger(propertyId) && propertyId > 0;
  const [details, setDetails] = useState<PropertyDetails | null>(null);
  const [loading, setLoading] = useState(hasValidPropertyId);
  const [error, setError] = useState<string | null>(null);
  const [poiCollapseState, setPoiCollapseState] = useState(() => ({
    propertyId,
    collapsedTypeIds: new Set<number>(),
  }));
  const currentUser = getCurrentUser();

  useEffect(() => {
    if (!hasValidPropertyId) return;

    let active = true;

    fetchPropertyDetails(propertyId)
      .then((property) => {
        if (active) setDetails(property);
      })
      .catch((requestError) => {
        if (!active) return;
        setError(requestError instanceof Error ? requestError.message : 'Could not load this property.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [hasValidPropertyId, propertyId]);

  const featureEntries = useMemo(() => details?.features
    ? Object.entries(details.features).filter(([key]) => !['property_id', 'snapshot_year', 'horizon_years'].includes(key))
    : [], [details]);

  const nearbyPoiGroups = useMemo(() => details ? groupNearbyPois(details.nearbyPois) : [], [details]);
  const collapsedPoiTypeIds = poiCollapseState.propertyId === propertyId
    ? poiCollapseState.collapsedTypeIds
    : new Set<number>();
  const returnClusterId = parsePositiveInteger(searchParams.get('clusterId'));
  const returnAreaName = searchParams.get('areaName');
  const shouldReturnToMarketMap = searchParams.get('returnTo') === 'map' && (returnClusterId !== null || details?.clusterId);
  const propertyClusterId = details?.clusterId ?? returnClusterId;

  const togglePoiGroup = (typeId: number) => {
    setPoiCollapseState((currentState) => {
      const nextTypeIds = currentState.propertyId === propertyId
        ? new Set(currentState.collapsedTypeIds)
        : new Set<number>();

      if (nextTypeIds.has(typeId)) {
        nextTypeIds.delete(typeId);
      } else {
        nextTypeIds.add(typeId);
      }

      return {
        propertyId,
        collapsedTypeIds: nextTypeIds,
      };
    });
  };

  const goToMarketMapPolygon = () => {
    if (!propertyClusterId) {
      navigate('/dashboard?tab=properties');
      return;
    }

    navigate(marketMapPolygonUrl(hasValidPropertyId ? propertyId : null, propertyClusterId, returnAreaName));
  };

  const goBack = () => {
    if (shouldReturnToMarketMap) {
      goToMarketMapPolygon();
      return;
    }

    navigate('/dashboard?tab=properties');
  };

  const handleLogout = () => {
    clearCurrentUser();
    navigate('/');
  };

  const detailFields = details ? [
    ['Property ID', details.propertyId],
    ['City', details.cityName],
    ['Latitude', formatCoordinate(details.lat)],
    ['Longitude', formatCoordinate(details.lon)],
    ['Location accuracy', details.locationAccuracy],
    ['Rooms', details.numRooms],
    ['Building year', details.buildingYear],
    ['Building floors', details.buildingFloors],
    ['Property type', details.propertyType],
    ['Latest sale price', details.latestSalePrice === null ? null : `₪${formatNumber(details.latestSalePrice)}`],
    ['Latest sale date', formatDate(details.latestSaleDate)],
  ] : [];

  return (
    <ConfigProvider theme={dashboardTheme}>
      <div className="app-shell">
        <header className="dashboard-header">
          {currentUser && <div className="dashboard-welcome">Welcome, {currentUser.firstName}</div>}
          <div className="dashboard-brand"><img src={propCastLogo} alt="PropCast" /></div>
          <Button className="dashboard-logout" onClick={handleLogout}>Log out</Button>
        </header>

        <main className="dashboard-main property-detail-main">
          <Button className="property-detail-back" type="text" icon={<ArrowLeftOutlined />} onClick={goBack}>
            {shouldReturnToMarketMap ? 'Back to market map' : 'Back to properties'}
          </Button>

          {loading && (
            <section className="property-detail-page property-detail-page--status" aria-busy="true">
              Loading property details…
            </section>
          )}

          {!hasValidPropertyId && (
            <section className="property-detail-page property-detail-page--status">
              <h1>Property details unavailable</h1>
              <p>The property ID in this URL is invalid.</p>
              <Button type="primary" onClick={goBack}>Return to properties</Button>
            </section>
          )}

          {hasValidPropertyId && !loading && error && (
            <section className="property-detail-page property-detail-page--status">
              <h1>Property details unavailable</h1>
              <p>{error}</p>
              <Button type="primary" onClick={goBack}>Return to properties</Button>
            </section>
          )}

          {hasValidPropertyId && !loading && details && (
            <article className="property-detail-page">
              <div className="property-detail-page__hero">
                <div>
                  <span className="section-kicker">Property details</span>
                  <h1>Property #{details.propertyId}</h1>
                  <p className="property-detail-page__address">{propertyAddress(details)}</p>
                </div>
                <div className="property-detail-page__actions">
                  {details.clusterId && (
                    <button className="property-detail-page__action" type="button" onClick={goToMarketMapPolygon}>
                      <AimOutlined /> View polygon
                    </button>
                  )}
                  <a className="property-detail-page__action" href={googleMapsUrl(details)} target="_blank" rel="noreferrer">
                    <EnvironmentOutlined /> Open location
                  </a>
                  <a className="property-detail-page__action property-detail-page__action--primary" href={yad2SearchUrl(details)} target="_blank" rel="noreferrer">
                    <LinkOutlined /> Browse on Yad2
                  </a>
                </div>
              </div>

              <div className="property-detail-page__summary">
                <section className="property-location-card">
                  {details.lat !== null && details.lon !== null ? (
                    <iframe
                      className="property-location-card__map"
                      title={`Map location for property ${details.propertyId}`}
                      src={openStreetMapEmbedUrl(details.lat, details.lon)}
                      loading="lazy"
                    />
                  ) : (
                    <div className="property-location-card__empty">
                      <HomeOutlined />
                      <span>Location preview is unavailable</span>
                    </div>
                  )}
                  <div className="property-location-card__caption">
                    <EnvironmentOutlined />
                    <span>Property location</span>
                  </div>
                </section>

                <section className="property-detail-page__transaction">
                  <span className="section-kicker">Most recent transaction</span>
                  <strong>{details.latestSalePrice === null ? '—' : `₪${formatNumber(details.latestSalePrice)}`}</strong>
                  <span>{formatDate(details.latestSaleDate)}</span>
                  <p>Yad2 photos and a direct listing URL are not included in this transaction dataset. The Yad2 button opens current sale listings without implying a match.</p>
                </section>
              </div>

              <section className="property-detail-page__section">
                <h2>Property information</h2>
                <dl className="property-details__grid">
                  {detailFields.map(([label, value]) => (
                    <div key={String(label)}>
                      <dt>{label}</dt>
                      <dd>{value === null || value === undefined || value === '' ? '—' : String(value)}</dd>
                    </div>
                  ))}
                </dl>
              </section>

              <section className="property-detail-page__section">
                <h2>Nearby points of interest</h2>
                {details.nearbyPois.length === 0 && <p className="property-details__empty">No POIs were found within 10 km.</p>}
                {nearbyPoiGroups.length > 0 && (
                  <div className="nearby-poi-groups">
                    {nearbyPoiGroups.map((group) => {
                      const isCollapsed = collapsedPoiTypeIds.has(group.typeId);
                      const panelId = `nearby-poi-group-${details.propertyId}-${group.typeId}`;

                      return (
                        <div className="nearby-poi-group" key={group.typeId}>
                          <button
                            className="nearby-poi-group__summary"
                            type="button"
                            aria-controls={panelId}
                            aria-expanded={!isCollapsed}
                            onClick={() => togglePoiGroup(group.typeId)}
                          >
                            <span className="nearby-poi-group__indicator" aria-hidden="true">
                              {isCollapsed ? '+' : '-'}
                            </span>
                            <span className="nearby-poi-group__title">
                              <span className="nearby-poi-group__type">{group.typeName}</span>
                              <span className="nearby-poi-group__meta">
                                {formatNumber(group.items.length)} {group.items.length === 1 ? 'place' : 'places'}, nearest {formatNumber(group.nearestDistanceMeters)} m
                              </span>
                            </span>
                            <span className="nearby-poi-group__sources">
                              {group.currentCount > 0 && <Tag color="blue">{formatNumber(group.currentCount)} current</Tag>}
                              {group.futureCount > 0 && <Tag color="gold">{formatNumber(group.futureCount)} future</Tag>}
                            </span>
                          </button>

                          {!isCollapsed && (
                            <div className="nearby-poi-list" id={panelId}>
                              {group.items.map((poi, index) => (
                                <div className="nearby-poi" key={`${poi.source}-${poi.typeId}-${poi.distanceMeters}-${poi.plannedYear ?? 'none'}-${index}`}>
                                  <Tag color={poi.source === 'future' ? 'gold' : 'blue'}>{poi.source}</Tag>
                                  <span className="nearby-poi__distance">{formatNumber(poi.distanceMeters)} m</span>
                                  {poi.plannedYear !== null && poi.plannedYear !== undefined && <span className="nearby-poi__planned">planned {poi.plannedYear}</span>}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>

              <section className="property-detail-page__section">
                <h2>
                  Stored feature snapshot
                  {details.featuresSnapshotYear && ` (${details.featuresSnapshotYear}, ${details.featuresHorizonYears ?? '—'} year horizon)`}
                </h2>
                {featureEntries.length === 0 && <p className="property-details__empty">No feature snapshot is available.</p>}
                <dl className="property-details__grid property-details__grid--features">
                  {featureEntries.map(([key, value]) => (
                    <div key={key}>
                      <dt>{formatFeatureLabel(key)}</dt>
                      <dd>{formatFeatureValue(value)}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            </article>
          )}
        </main>
      </div>
    </ConfigProvider>
  );
};

export default PropertyDetailsPage;
