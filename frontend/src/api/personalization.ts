// Mock personalization API (Saved Searches + Watchlist).
// Backed by localStorage so data persists between reloads and the UI feels real.
// Swap these functions for real HTTP calls once the backend endpoints exist.

export type SearchFilters = {
  city?: string;
  slider?: [number, number];
  yearsForward?: string;
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

// In a real app this comes from the authenticated session. Mocked for now.
const MOCK_USER_KEY = 'me';
const SAVED_SEARCHES_KEY = `propcast.${MOCK_USER_KEY}.savedSearches`;
const WATCHLIST_KEY = `propcast.${MOCK_USER_KEY}.watchlist`;
const SEED_FLAG_KEY = `propcast.${MOCK_USER_KEY}.seeded`;

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

// Seed a couple of example items the first time, so the dashboard isn't empty.
const seedIfNeeded = (): void => {
  if (localStorage.getItem(SEED_FLAG_KEY)) return;

  const now = new Date().toISOString();
  const seededSearches: SavedSearch[] = [
    {
      id: createId(),
      name: 'תל אביב · עד ₪3M · 5 שנים',
      filters: { city: 'תל אביב - יפו', slider: [0, 3_000_000], yearsForward: '5' },
      createdAt: now,
    },
    {
      id: createId(),
      name: 'חיפה · תקציב נמוך · 3 שנים',
      filters: { city: 'חיפה', slider: [0, 1_500_000], yearsForward: '3' },
      createdAt: now,
    },
  ];

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

  writeJson(SAVED_SEARCHES_KEY, seededSearches);
  writeJson(WATCHLIST_KEY, seededWatchlist);
  localStorage.setItem(SEED_FLAG_KEY, '1');
};

/* ——— Saved Searches ——— */

export const listSavedSearches = (): Promise<SavedSearch[]> => {
  seedIfNeeded();
  const items = readJson<SavedSearch[]>(SAVED_SEARCHES_KEY, []);
  return delay(items);
};

export const createSavedSearch = (
  name: string,
  filters: SearchFilters,
): Promise<SavedSearch> => {
  seedIfNeeded();
  const items = readJson<SavedSearch[]>(SAVED_SEARCHES_KEY, []);
  const saved: SavedSearch = {
    id: createId(),
    name: name.trim() || 'חיפוש ללא שם',
    filters,
    createdAt: new Date().toISOString(),
  };
  writeJson(SAVED_SEARCHES_KEY, [saved, ...items]);
  return delay(saved);
};

export const deleteSavedSearch = (id: string): Promise<void> => {
  const items = readJson<SavedSearch[]>(SAVED_SEARCHES_KEY, []);
  writeJson(
    SAVED_SEARCHES_KEY,
    items.filter((item) => item.id !== id),
  );
  return delay(undefined);
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
