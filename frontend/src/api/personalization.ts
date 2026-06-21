// Personalization API.
// Saved Searches are persisted per-user on the backend (Postgres) and reached
// over HTTP with the JWT auth cookie. The Watchlist is still a localStorage mock.

const API_BASE_URL = 'http://localhost:4000';

export type SearchFilters = {
  city?: string;
  slider?: [number, number];
  yearsForward?: string;
  roomsRange?: [number, number];
};

export type SavedSearch = {
  id: string;
  name: string;
  filters: SearchFilters;
  createdAt: string;
};

export type WatchlistItem = {
  id: string;
  areaName: string;
  growthPercent: number;
  cities: string[];
  note?: string;
  createdAt: string;
};

const WATCHLIST_KEY = 'propcast.me.watchlist';
const SEED_FLAG_KEY = 'propcast.me.seeded';

const NETWORK_DELAY_MS = 250;

const delay = <T>(value: T): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(value), NETWORK_DELAY_MS));

const createId = (): string =>
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

const readJson = <T>(key: string, fallback: T): T => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
};

const writeJson = (key: string, value: unknown): void => {
  localStorage.setItem(key, JSON.stringify(value));
};

// Seed a watchlist example the first time, so the dashboard isn't empty.
const seedIfNeeded = (): void => {
  if (localStorage.getItem(SEED_FLAG_KEY)) return;

  const now = new Date().toISOString();
  const seededWatchlist: WatchlistItem[] = [
    {
      id: createId(),
      areaName: 'חדרה, אור עקיבא',
      growthPercent: 12.4,
      cities: ['חדרה', 'אור עקיבא'],
      note: 'תחנת רכבת מתוכננת באזור',
      createdAt: now,
    },
  ];

  writeJson(WATCHLIST_KEY, seededWatchlist);
  localStorage.setItem(SEED_FLAG_KEY, '1');
};

/* ——— Saved Searches (server-side, per authenticated user) ——— */

const apiRequest = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = (data && (data.message || data.error)) || 'Request failed';
    throw new Error(Array.isArray(message) ? message.join(', ') : message);
  }

  return data as T;
};

export const listSavedSearches = (): Promise<SavedSearch[]> =>
  apiRequest<SavedSearch[]>('/saved-searches');

export const createSavedSearch = (
  name: string,
  filters: SearchFilters,
): Promise<SavedSearch> =>
  apiRequest<SavedSearch>('/saved-searches', {
    method: 'POST',
    body: JSON.stringify({ name, filters }),
  });

export const deleteSavedSearch = async (id: string): Promise<void> => {
  await apiRequest<{ ok: boolean }>(`/saved-searches/${id}`, { method: 'DELETE' });
};

/* ——— Watchlist (followed areas) ——— */

export const listWatchlist = (): Promise<WatchlistItem[]> => {
  seedIfNeeded();
  const items = readJson<WatchlistItem[]>(WATCHLIST_KEY, []);
  return delay(items);
};

export const addToWatchlist = (
  item: Omit<WatchlistItem, 'id' | 'createdAt'>,
): Promise<WatchlistItem> => {
  seedIfNeeded();
  const items = readJson<WatchlistItem[]>(WATCHLIST_KEY, []);

  // Dedupe by area name so the same area isn't followed twice.
  const existing = items.find((entry) => entry.areaName === item.areaName);
  if (existing) return delay(existing);

  const saved: WatchlistItem = {
    ...item,
    id: createId(),
    createdAt: new Date().toISOString(),
  };
  writeJson(WATCHLIST_KEY, [saved, ...items]);
  return delay(saved);
};

export const removeFromWatchlist = (id: string): Promise<void> => {
  const items = readJson<WatchlistItem[]>(WATCHLIST_KEY, []);
  writeJson(
    WATCHLIST_KEY,
    items.filter((item) => item.id !== id),
  );
  return delay(undefined);
};
