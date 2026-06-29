const API_BASE_URL = 'http://localhost:4000';

export type PublicUser = {
  userId: number;
  email: string;
  phone: string;
  username: string;
  firstName: string;
  lastName: string;
};

export type LoginPayload = {
  identifier: string;
  password: string;
};

export type SignupPayload = {
  email: string;
  phone: string;
  username: string;
  firstName: string;
  lastName: string;
  password: string;
};

const request = async <T>(path: string, body: unknown): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = (data && (data.message || data.error)) || 'Request failed';
    throw new Error(Array.isArray(message) ? message.join(', ') : message);
  }

  return data as T;
};

export const login = (payload: LoginPayload) =>
  request<{ user: PublicUser }>('/auth/login', payload);

export const signup = (payload: SignupPayload) =>
  request<{ user: PublicUser }>('/auth/signup', payload);

const CURRENT_USER_KEY = 'propcast:currentUser';

export const setCurrentUser = (user: PublicUser): void => {
  localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user));
};

export const getCurrentUser = (): PublicUser | null => {
  const raw = localStorage.getItem(CURRENT_USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PublicUser;
  } catch {
    return null;
  }
};

export const clearCurrentUser = (): void => {
  localStorage.removeItem(CURRENT_USER_KEY);
};
