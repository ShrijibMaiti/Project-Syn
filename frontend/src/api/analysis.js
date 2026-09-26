/**
 * Calls for the two analysis views: Sensitivity and the Risk Map.
 *
 * Unlike the measurement pages, these have NO captured fixture on purpose. A
 * counterfactual computed from placeholder numbers would be a fabricated spec,
 * and a blast radius drawn on an invented graph would be a fabricated risk. When
 * no gate API is reachable the pages say so instead of showing anything.
 *
 * Returns { status: 'ok', data } | { status: 'unavailable' } | { status: 'error', message }.
 */

import { apiClient, ApiUnavailableError } from './client.js';

/** The run chosen via `?run=` in the page URL, or 'latest'. */
const selectedRun = () => new URLSearchParams(window.location.search).get('run') || 'latest';

async function fetchAnalysis(path, params = {}, options) {
  const query = new URLSearchParams({ commit: selectedRun(), ...params });
  try {
    return { status: 'ok', data: await apiClient.get(`${path}?${query}`, options) };
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    if (error instanceof ApiUnavailableError) return { status: 'unavailable' };
    return { status: 'error', message: error.message };
  }
}

/** GET /sensitivity — what would flip this run's verdict, computed from its laws. */
export const getSensitivity = (ceilingS = 30, options) =>
  fetchAnalysis('/sensitivity', { ceiling_s: String(ceilingS) }, options);

/** GET /riskmap — static call graph + measured overlay + blast radius. */
export const getRiskMap = (options) => fetchAnalysis('/riskmap', {}, options);
