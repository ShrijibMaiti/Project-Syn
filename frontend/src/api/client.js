/**
 * Thin fetch wrapper for the SYN gate API.
 *
 * Two data sources, same responses:
 *
 *  - LIVE API: VITE_API_BASE_URL points at a running gate API (`uvicorn
 *    gateway.api:app`), e.g. http://localhost:8000/api.
 *  - STATIC (CI): VITE_DATA_BASE_URL points at the JSON that CI publishes to
 *    the repo's `syn-runs` branch, e.g.
 *    https://raw.githubusercontent.com/<owner>/<repo>/syn-runs/api
 *    Every run there was measured on a GitHub Actions runner; no server needed.
 *    gateway/export_static.py writes those files by calling the same handlers
 *    the API uses, with the path mapping in `staticPath` below.
 *
 * With neither set, every request short-circuits with an ApiUnavailableError
 * so callers in endpoints.js fall back to the captured run fixtures.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const DATA_URL = (import.meta.env.VITE_DATA_BASE_URL || '').replace(/\/$/, '');

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

/** True when the dashboard reads CI-published files instead of a live API. */
export const isStaticMode = () => !BASE_URL && Boolean(DATA_URL);

export const isApiConfigured = () => Boolean(BASE_URL || DATA_URL);

/**
 * API path -> published file. MUST match gateway/export_static.py static_path:
 * strip the leading "/", drop commit=latest, sort query keys, append
 * "__<key>-<value>" per parameter, then ".json".
 *   /stability/default?commit=pr-7-abc1234 -> stability/default__commit-pr-7-abc1234.json
 */
export function staticPath(path) {
  const [rawPath, query = ''] = path.split('?');
  const params = [...new URLSearchParams(query)]
    .filter(([k, v]) => !(k === 'commit' && v === 'latest'))
    .sort(([a, av], [b, bv]) => (a === b ? (av < bv ? -1 : 1) : a < b ? -1 : 1));
  const file =
    decodeURIComponent(rawPath).replace(/^\//, '') +
    params.map(([k, v]) => `__${k}-${v}`).join('') +
    '.json';
  return file.split('/').map(encodeURIComponent).join('/');
}

async function requestStatic(path, { signal } = {}) {
  // raw.githubusercontent.com caches for ~5 minutes; a per-minute query string
  // keeps a freshly published run from hiding behind a stale copy.
  const bust = Math.floor(Date.now() / 60000);
  const response = await fetch(`${DATA_URL}/${staticPath(path)}?t=${bust}`, {
    signal,
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    // A missing file is exactly what the API's 404 would have been.
    throw new ApiError(response.status === 404 ? 404 : response.status, path, '');
  }
  return response.json();
}

async function request(path, { method = 'GET', body, signal, headers } = {}) {
  if (!BASE_URL && DATA_URL && method === 'GET') return requestStatic(path, { signal });
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
