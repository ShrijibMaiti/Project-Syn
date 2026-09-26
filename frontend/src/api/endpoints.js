/**
 * Typed calls, one per route.
 *
 * Hits the gate API when VITE_API_BASE_URL is configured and falls back to the
 * captured run fixtures otherwise, so the views render the same evidence either
 * way. Live responses are RAW MEASUREMENTS; adapters.js translates them into the
 * shapes the pages consume.
 *
 * Set VITE_API_BASE_URL to the API root INCLUDING /api, e.g.
 *   VITE_API_BASE_URL=http://localhost:8000/api
 *
 * RUN SELECTION: `?run=<commit>` in the page URL chooses which stored run to
 * view (e.g. ?run=demo-faulty vs ?run=demo-clean). Without it the backend serves
 * its latest run.
 */

import { apiClient, ApiUnavailableError } from './client.js';
import {
  adaptBlind,
  adaptComplexity,
  adaptEvidence,
  adaptLanding,
  adaptStability,
} from './adapters.js';
import {
  BLIND_DETECTION,
  COMPLEXITY,
  EVIDENCE,
  LANDING,
  RUN,
  STABILITY,
  VERDICTS,
  VERDICT_STATES,
} from './fixtures.js';

/* ------------------------------------------------------------------ *
 * Run selection
 * ------------------------------------------------------------------ */

/** The run chosen via `?run=` in the URL, or 'latest'. */
export const selectedRun = () =>
  new URLSearchParams(window.location.search).get('run') || 'latest';

/** Append `commit=<run>` to a path unless viewing the latest run. */
const withRun = (path) => {
  const run = selectedRun();
  if (run === 'latest') return path;
  const sep = path.includes('?') ? '&' : '?';
  return `${path}${sep}commit=${encodeURIComponent(run)}`;
};

/* ------------------------------------------------------------------ *
 * Formatting
 * ------------------------------------------------------------------ */

const ok = (v) => v !== null && v !== undefined && Number.isFinite(Number(v));
const f2 = (v, d = 2) => (ok(v) ? Number(v).toFixed(d) : '—');
const sci = (v, d = 2) => (ok(v) ? Number(v).toExponential(d) : '—');
const int = (v) => (ok(v) ? Math.round(Number(v)).toLocaleString('en-US') : '—');

/** Backend stores created_at as epoch seconds; render as 2026-09-26 07:03:14Z. */
export const formatTimestamp = (epoch) =>
  ok(epoch)
    ? new Date(Number(epoch) * 1000).toISOString().replace('T', ' ').replace(/\.\d+Z$/, 'Z')
    : null;

/** Backend risk words -> the four certificate states. */
export const toState = (risk) => {
  const r = (risk || '').toUpperCase();
  if (r === 'REFUSE') return 'REFUSED';
  if (r === 'OK') return 'PASS';
  return VERDICT_STATES.includes(r) ? r : 'UNKNOWN';
};

/* ------------------------------------------------------------------ *
 * Transport
 * ------------------------------------------------------------------ */

async function live(path, fixture, adapt, options) {
  try {
    const raw = await apiClient.get(path, options);
    return adapt ? adapt(raw, fixture) : raw;
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    if (!(error instanceof ApiUnavailableError)) {
      console.warn(`[syn] ${error.message} — falling back to captured run fixture`);
    }
    return fixture;
  }
}

/* ------------------------------------------------------------------ *
 * Routes
 * ------------------------------------------------------------------ */

/** GET /landing — proof numbers composed from the stored run. */
export const getLanding = (options) => live('/landing', LANDING, adaptLanding, options);

/** GET /stability/default — capacity sweep over N (concurrency). */
export const getStability = (options) =>
  live(withRun('/stability/default'), STABILITY, adaptStability, options);

/** GET /complexity/default — multiscale sweep over n (input size). */
export const getComplexity = (options) =>
  live(withRun('/complexity/default'), COMPLEXITY, adaptComplexity, options);

/** GET /evidence — M0 vs M1 comparison behind the stability verdict. */
export const getEvidence = (options) =>
  live(withRun('/evidence'), EVIDENCE, adaptEvidence, options);

/** GET /blind — labels-stripped classification run, all seeds.
 *  Not run-scoped: blind detection validates the detector, not a commit. */
export const getBlindDetection = (options) =>
  live('/blind', BLIND_DETECTION, adaptBlind, options);

/** GET /runs — recent gate runs, for a run picker. */
export const getRuns = (options) => live('/runs', { runs: [] }, null, options);

/** GET /calibration — the instrument's own noise floor. */
export const getCalibration = (options) => live('/calibration', null, null, options);

/* ------------------------------------------------------------------ *
 * Run metadata for the app chrome (cached per run)
 * ------------------------------------------------------------------ */

const metaCache = new Map();

/**
 * Commit, recorded time and verdict for the selected run — what the top bar
 * shows on every page. Falls back to the fixture, clearly flagged live=false,
 * so the chrome never presents captured data as a measurement.
 */
export function getRunMeta() {
  const run = selectedRun();
  if (!metaCache.has(run)) {
    const pending = apiClient
      .get(`/verdict/${encodeURIComponent(run)}`)
      .then((raw) => ({
        live: true,
        commit: raw.commit,
        timestamp: formatTimestamp(raw.created_at),
        state: toState(raw.risk),
      }))
      .catch(() => {
        metaCache.delete(run); // retry once the backend comes up
        return {
          live: false,
          commit: RUN.commitShort,
          timestamp: RUN.displayTimestamp,
          state: null,
        };
      });
    metaCache.set(run, pending);
  }
  return metaCache.get(run);
}

/* ------------------------------------------------------------------ *
 * Verdict — the whole certificate built from the measured run
 * ------------------------------------------------------------------ */

function summaryFor(state, flagged, total) {
  if (state === 'REFUSED')
    return `Merge blocked. ${flagged} of ${total} lenses flagged this change. The grounds are attached below.`;
  if (state === 'WARN')
    return `Merge allowed with a recorded objection. ${flagged} of ${total} lenses approached a gate threshold without crossing it.`;
  if (state === 'PASS')
    return `Merge allowed. Neither lens found evidence of a structural risk in the measured range.`;
  return 'SYN could not gather enough evidence to decide. This is not a pass.';
}

function complexityLens(probe) {
  const e = probe?.evidence ?? {};
  if (!probe || !ok(e.exponent)) {
    return {
      target: e.target ?? '—',
      exponent: '—',
      ci: probe ? 'insufficient evidence' : 'not measured',
      superlinear: false,
      superlinearLabel: 'NOT MEASURED',
    };
  }
  const ci = Array.isArray(e.exponent_ci) ? e.exponent_ci : null;
  return {
    target: e.target,
    exponent: f2(e.exponent),
    ci: ci ? `CI 95% [${f2(ci[0])}, ${f2(ci[1])}]` : 'tail-slope estimate',
    superlinear: Boolean(e.superlinear),
    superlinearLabel: `SUPERLINEAR — ${e.superlinear ? 'TRUE' : 'FALSE'}`,
  };
}

function stabilityLens(probe) {
  const e = probe?.evidence ?? {};
  if (!probe || !ok(e.kappa)) {
    return [{ k: 'STATUS', v: probe ? 'insufficient evidence' : 'not measured' }];
  }
  const rows = [
    { k: 'COHERENCY COST κ', v: sci(e.kappa) },
    { k: 'F-TEST P-VALUE', v: sci(e.p_value) },
    { k: 'EVIDENCE', v: e.evidence ? 'DETECTED' : 'NONE' },
  ];
  if (e.evidence && ok(e.peak_throughput)) {
    rows.push({ k: 'PEAK THROUGHPUT', v: `${int(e.peak_throughput)} rps` });
    rows.push({ k: 'PEAK AT', v: `N = ${int(e.peak_n)}` });
  }
  rows.push(
    ok(e.separatrix)
      ? { k: 'SEPARATRIX', v: `N = ${f2(e.separatrix, 1)}` }
      : { k: 'SEPARATRIX', v: 'none' },
  );
  if (ok(e.headroom)) rows.push({ k: 'HEADROOM', v: `${f2(e.headroom)}×` });
  return rows;
}

function remediationFor(state, comp, stab) {
  if (state !== 'REFUSED' && state !== 'WARN') return [];
  const ce = comp?.evidence ?? {};
  const se = stab?.evidence ?? {};
  const steps = [];
  if (ce.superlinear) {
    const ci = Array.isArray(ce.exponent_ci)
      ? ` (CI ${f2(ce.exponent_ci[0])}–${f2(ce.exponent_ci[1])})`
      : '';
    steps.push({
      title: `Bring the growth exponent of ${ce.target} below the 1.2 gate threshold.`,
      body: `Measured exponent ${f2(ce.exponent)}${ci}. Replace nested scans with a keyed index, batch per-item queries, or bound the input size — then re-run the gate to confirm the exponent has dropped.`,
    });
  }
  if (se.evidence) {
    const sep = ok(se.separatrix) ? ` and a separatrix at N = ${f2(se.separatrix, 1)}` : '';
    steps.push({
      title: `Reduce coherency cost on ${se.target}, or cap concurrency below the cliff.`,
      body: `κ = ${sci(se.kappa)} (p = ${sci(se.p_value)}). Throughput peaks at N = ${int(se.peak_n)}${sep}. Reduce shared-state contention, or enforce an admission limit that keeps concurrency on the healthy side of the separatrix.`,
    });
  }
  return steps.map((s, i) => ({ num: String(i + 1), ...s }));
}

/**
 * GET /verdict/{run} — the refusal certificate.
 *
 * When a backend answers, EVERY field is built from the measured run: meta
 * rows, both lens panels, findings, remediation and timings. `state` only
 * selects a fixture when no backend is reachable — a demo toggle must never
 * override a measured result.
 */
export const getVerdict = async (state, options) => {
  const key = VERDICT_STATES.includes(state) ? state : 'REFUSED';
  try {
    const raw = await apiClient.get(`/verdict/${encodeURIComponent(selectedRun())}`, options);
    const mapped = toState(raw.risk);
    const base = VERDICTS[mapped] ?? VERDICTS.UNKNOWN ?? VERDICTS[key];

    const probes = raw.probes ?? [];
    const comp = probes.find((p) => p.kind === 'complexity');
    const stab = probes.find((p) => p.kind === 'stability');
    const flagged = probes.filter((p) => p.risk === 'refuse' || p.risk === 'warn').length;
    const measured = probes.filter((p) => p.risk !== 'unknown').length;
    const stamp = formatTimestamp(raw.created_at);

    // Backend timings are a DICT {probe: seconds}; the UI wants an array.
    // "_wall" is total wall clock, not a probe.
    const timings = Object.entries(raw.timings ?? {})
      .filter(([name, s]) => name !== '_wall' && Number(s) >= 0)
      .map(([name, seconds]) => ({ name, seconds: Number(seconds) }));
    const wall = raw.timings?._wall;
    const totalWallClock = ok(wall)
      ? `${Number(wall).toFixed(1)} s`
      : `${timings.reduce((acc, t) => acc + t.seconds, 0).toFixed(1)} s`;

    // Reasons are formatted strings: "[complexity/refuse] order_report: ..."
    const findings = (raw.reasons ?? []).map((r) => {
      const m = /^\[([^\]]+)\]\s*(.*)$/.exec(r) ?? [];
      const tag = m[1] ?? 'probe';
      const risky = /refuse/i.test(tag)
        ? 'HIGH'
        : /warn|escalated/i.test(tag)
          ? 'MED'
          : /unknown/i.test(tag)
            ? 'UNKNOWN' // could not decide -- never shown as OK
            : 'OK';
      return { probe: tag.replace('/', '.'), finding: m[2] ?? r, risk: risky };
    });

    return {
      ...base,
      live: true,
      state: mapped,
      summary: summaryFor(mapped, flagged, probes.length),
      commit: raw.commit,
      timestamp: stamp,
      certificate: [
        { k: 'COMMIT', v: raw.commit },
        { k: 'RECORDED', v: stamp ?? '—' },
        { k: 'SOURCE', v: 'LIVE GATE RUN' },
        {
          k: 'EVIDENCE',
          v: `${measured === probes.length ? 'COMPLETE' : 'PARTIAL'} — ${measured} / ${probes.length} LENSES`,
        },
        { k: 'CERT ID', v: `syn-${raw.commit}-${(stamp ?? '').slice(11, 16).replace(':', '')}` },
      ],
      complexity: complexityLens(comp),
      stability: stabilityLens(stab),
      stabilityTarget: stab?.evidence?.target ?? '—',
      remediation: remediationFor(mapped, comp, stab),
      certificateText: raw.certificate ?? base.certificateText,
      findings: findings.length ? findings : base.findings,
      timings,
      totalWallClock,
    };
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    if (!(error instanceof ApiUnavailableError)) {
      console.warn(`[syn] ${error.message} — falling back to captured run fixture`);
    }
    return { ...VERDICTS[key], live: false };
  }
};
