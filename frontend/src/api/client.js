/**
 * Thin fetch wrapper for the SYN gate API.
 *
 * The base URL comes from VITE_API_BASE_URL. When it is not set — which is the
 * case until a gate backend is deployed — every request short-circuits with an
 * ApiUnavailableError so callers in endpoints.js can fall back to the captured
 * run fixtures without spraying network errors into the console.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export class ApiUnavailableError extends Error {
  constructor(path) {
    super(`No SYN API configured (VITE_API_BASE_URL unset) — skipped ${path}`);
    this.name = 'ApiUnavailableError';
  }
}

export class ApiError extends Error {
  constructor(status, path, body) {
    super(`SYN API ${status} on ${path}${body ? ` — ${body}` : ''}`);
    this.name = 'ApiError';
    this.status = status;
    this.path = path;
  }
}

export const isApiConfigured = () => Boolean(BASE_URL);

async function request(path, { method = 'GET', body, signal, headers } = {}) {
  if (!BASE_URL) throw new ApiUnavailableError(path);

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    signal,
    headers: {
      Accept: 'application/json',
      ...(body ? { 'Content-Type': 'application/json' } : null),
      ...headers,
    },
    ...(body ? { body: JSON.stringify(body) } : null),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new ApiError(response.status, path, text);
  }

  if (response.status === 204) return null;
  return response.json();
}

export const apiClient = {
  get: (path, options) => request(path, { ...options, method: 'GET' }),
  post: (path, body, options) => request(path, { ...options, method: 'POST', body }),
};
