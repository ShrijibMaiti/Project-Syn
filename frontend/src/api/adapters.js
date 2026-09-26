/**
 * Backend -> view-model adapters.
 *
 * The gate API emits RAW MEASUREMENTS (latency in seconds, throughput, fit
 * parameters). The pages consume presentational shapes (tuple points, stat
 * cards, formatted strings). These functions are the only place that
 * translation happens, so components and fixtures stay untouched.
 *
 * Every adapter degrades to the fixture when a field is missing, so a partial
 * backend response never blanks a page.
 */

const num = (v, digits = 2) =>
  v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : Number(v).toFixed(digits);

const sci = (v, digits = 2) =>
  v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : Number(v).toExponential(digits);

const int = (v) =>
  v === null || v === undefined || Number.isNaN(Number(v))
    ? '—'
    : Math.round(Number(v)).toLocaleString('en-US');

/** spread is a max/min RATIO from the backend; the UI shows it as a CV percentage. */
const spreadPct = (s) => (s === null || s === undefined ? 0 : Math.max(0, (Number(s) - 1) * 100));

/**
 * Model A (no coherency) refit from the measured points.
 *
 * M0 is linear in its parameters:  R(N) = a + b·(N−1),  base = a, σ = b/a.
 * Fitted by weighted least squares with weights 1/R² — the same relative-error
 * weighting the backend uses — so it is Model A's OWN best fit, not Model B
 * with κ deleted. The two differ exactly when κ matters.
 */
function fitModelA(points) {
  let sw = 0, swx = 0, swxx = 0, swr = 0, swxr = 0;
  for (const [n, r] of points) {
    if (!(r > 0)) continue;
    const w = 1 / (r * r);
    const x = n - 1;
    sw += w; swx += w * x; swxx += w * x * x; swr += w * r; swxr += w * x * r;
  }
  const det = sw * swxx - swx * swx;
  let a = det !== 0 ? (swr * swxx - swx * swxr) / det : swr / sw;
  let b = det !== 0 ? (sw * swxr - swx * swr) / det : 0;
  if (!(b >= 0) || !(a > 0)) { b = 0; a = swr / sw; } // contention cannot be negative
  return { baseMs: a, sigma: b / a, kappa: 0 };
}

/* ------------------------------------------------------------------ *
 * STABILITY — x axis is N (CONCURRENCY)
 * ------------------------------------------------------------------ */

export function adaptStability(api, fallback) {
  if (!api?.points?.length) return fallback;

  const points = api.points.map((p) => [
    p.n,
    p.latency_s * 1000, // seconds -> ms
    p.throughput,
    spreadPct(p.spread),
  ]);

  // The measured peak, from the data itself.
  const peakRow = points.reduce((best, p) => (p[2] > best[2] ? p : best), points[0]);
  const last = points[points.length - 1];
  // Humped only if throughput actually falls after the peak.
  const humped = peakRow !== last && last[2] < peakRow[2] * 0.95;
  const declineFactor = humped ? peakRow[2] / last[2] : 1;

  const sigma = api.fit?.sigma ?? 0;
  const kappa = api.fit?.kappa ?? 0;
  const hasTrap = humped && api.trap?.separatrix != null && api.trap?.healthy_n != null;

  return {
    target: api.target ?? fallback.target,
    levels: api.measurement?.levels ?? points.length,
    nMax: api.measurement?.n_max ?? last[0],
    secondsPerLevel: fallback.secondsPerLevel,
    separatrix: hasTrap ? api.trap.separatrix : null,
    operatingPoint: hasTrap ? api.trap.healthy_n : null,
    humped,
    declineFactor,
    peak: { n: peakRow[0], throughput: Math.round(peakRow[2]) },
    // ideal service rate = 1 / base latency
    lambda: api.fit?.base ? 1 / api.fit.base : fallback.lambda,
    models: {
      a: fitModelA(points),                                        // M0 — its own fit
      b: { baseMs: (api.fit?.base ?? 0) * 1000, sigma, kappa },    // M1 — backend fit
    },
    points,
    stats: [
      {
        label: humped ? 'PEAK THROUGHPUT' : 'MAX THROUGHPUT',
        value: `${int(peakRow[2])} rps`,
        note: humped ? `at N = ${int(peakRow[0])}` : `at N = ${int(peakRow[0])} — still rising`,
      },
      humped
        ? {
            label: `AT N = ${int(last[0])}`,
            value: `${num(last[2], 1)} rps`,
            note: `${num(declineFactor, 0)}× decline from peak`,
          }
        : {
            label: 'SHAPE',
            value: 'MONOTONE',
            note: 'throughput never falls — no collapse',
          },
      hasTrap
        ? {
            label: 'SEPARATRIX',
            value: `N = ${num(api.trap.separatrix, 1)}`,
            note: 'no self-recovery beyond',
          }
        : {
            label: 'SEPARATRIX',
            value: 'none',
            note: humped ? 'no trap at this operating load' : 'no peak, so no trap can exist',
          },
      hasTrap
        ? {
            label: 'HEADROOM',
            value: `${num(api.trap.headroom)}×`,
            note: `from operating point N = ${num(api.trap.healthy_n, 1)}`,
          }
        : {
            label: 'COHERENCY',
            value: api.evidence ? 'DETECTED' : 'NONE',
            note: `F-test p = ${sci(api.fit?.p_value)}`,
          },
    ],
  };
}

/* ------------------------------------------------------------------ *
 * COMPLEXITY — x axis is n (INPUT SIZE)
 * ------------------------------------------------------------------ */

export function adaptComplexity(api, fallback) {
  if (!api?.points?.length) return fallback;

  const points = api.points.map((p) => [p.n, p.resource * 1000]); // seconds -> ms
  const exponent = api.law?.exponent ?? null;
  const ci = api.law?.exponent_ci ?? null;
  const superlinear = api.superlinear === true;
  const nMax = api.measurement?.n_max ?? points[points.length - 1][0];

  // Fixed per-call overhead: the flat region at small n. Without it a pure
  // power law dives toward zero and misses the low-n measurements entirely.
  const floor = Math.min(...points.map((p) => p[1])) * 0.9;

  // Coefficient from the asymptotic tail, AFTER removing the floor.
  const tail = points[points.length - 1];
  const coefficient =
    exponent && exponent > 0
      ? Math.max(tail[1] - floor, 1e-12) / Math.pow(tail[0], exponent)
      : fallback.law.coefficient;

  const ceiling = fallback.ceiling; // ms — declared operating ceiling
  // Detonation is only meaningful for SUPERLINEAR growth. Extrapolating a
  // linear law to a ceiling yields a real-looking but meaningless number.
  const detonation =
    superlinear && exponent > 0 && ceiling > floor
      ? Math.pow((ceiling - floor) / coefficient, 1 / exponent)
      : null;

  // Pivot the exponent band inside the fitted (upper) region.
  const anchor = points[Math.min(points.length - 1, Math.floor(points.length * 0.75))][0];

  return {
    target: api.target ?? fallback.target,
    scales: points.length,
    superlinear,
    law: {
      coefficient,
      exponent: exponent ?? fallback.law.exponent,
      exponentLow: ci ? ci[0] : (exponent ?? 0) - 0.06,
      exponentHigh: ci ? ci[1] : (exponent ?? 0) + 0.06,
      anchor,
      floor,
      display: `cost(n) ≈ ${num(floor, 2)} + ${sci(coefficient)} · n^${num(exponent)} ms`,
    },
    ceiling,
    ceilingLabel: fallback.ceilingLabel,
    points,
    stats: [
      {
        label: 'GROWTH EXPONENT',
        value: num(exponent),
        note: ci ? `CI 95% [${num(ci[0])}, ${num(ci[1])}]` : 'tail-slope estimate',
      },
      {
        label: 'SUPERLINEAR',
        value: superlinear ? 'TRUE' : 'FALSE',
        note: superlinear ? 'gate signal — exponent > 1.2' : 'below the gate threshold',
      },
      detonation
        ? {
            label: 'DETONATION AT',
            value: `n ≈ ${int(detonation)}`,
            note: 'crosses the declared resource ceiling',
          }
        : {
            label: 'DETONATION',
            value: 'none',
            note: 'growth is not superlinear — no ceiling crossing to predict',
          },
      {
        label: 'MEASUREMENT RANGE',
        value: `${num(api.measurement?.decades, 1)} oom`,
        note: `n = ${int(api.measurement?.n_min)} → ${int(nMax)} · minimum 2.0`,
      },
    ],
  };
}

/* ------------------------------------------------------------------ *
 * EVIDENCE — M0 vs M1
 * ------------------------------------------------------------------ */

/**
 * Decision thresholds. These are METHOD CONSTANTS and must match the backend
 * (stability/capacity_curve.py: ALPHA, MIN_LEVELS, MIN_NMAX; the 10x noise
 * floor margin in stability/harness_calibration.py). They are shown to the
 * reader so every verdict states the bar it was held to.
 */
export const EVIDENCE_THRESHOLDS = { alpha: 0.01, minLevels: 16, minNMax: 256, floorMargin: 10 };

export function adaptEvidence(api, fallback) {
  if (!api || api.kappa === undefined || api.kappa === null) return fallback;

  const T = EVIDENCE_THRESHOLDS;
  const levels = api.measurement?.levels ?? null;
  const nMax = api.measurement?.n_max ?? null;
  const floor = api.noise_floor;
  const ratio = floor && api.kappa ? api.kappa / floor : null;
  const ciText = api.kappa_ci ? `[${sci(api.kappa_ci[0], 1)}, ${sci(api.kappa_ci[1], 1)}]` : '—';
  const sep = api.trap?.separatrix;

  // Four mutually exclusive outcomes, in the order the backend applies them.
  let outcome;
  if (!api.adequate) outcome = 'INSUFFICIENT';
  else if (!api.evidence) outcome = 'NONE';
  else if (api.exceeds_floor === false) outcome = 'NOISE';
  else outcome = 'TRAP';

  const selectedB = outcome === 'TRAP';
  // With an inadequate range neither model has won: say so, don't pick one.
  const undecided = outcome === 'INSUFFICIENT';
  const verdictA = undecided ? 'UNDECIDED' : selectedB ? 'REJECTED' : 'SELECTED';
  const verdictB = undecided ? 'UNDECIDED' : selectedB ? 'SELECTED' : 'REJECTED';
  const ratioText =
    ratio === null ? '—' : ratio >= 10 ? `${int(ratio)}×` : ratio >= 1 ? `${num(ratio, 1)}×` : '< 1×';

  const conclusions = {
    TRAP: {
      badge: 'EVIDENCE OF A TRAP',
      text: `There is a coherency cost on this service, and it is not an artifact of noise (F-test p = ${sci(api.p_value)} over ${int(levels)} sampled levels up to N = ${int(nMax)}; κ = ${sci(api.kappa)}, ${ratioText} the instrument's own noise floor). A positive κ means throughput must peak and then fall, so a separatrix exists${
        sep != null ? ` — it sits at N = ${num(sep, 1)}.` : ', though none falls within the assumed operating load.'
      }`,
    },
    NONE: {
      badge: 'NO EVIDENCE OF A TRAP',
      text: `Adding a coherency term does not explain the data better than chance (F-test p = ${sci(api.p_value)}, above α = ${T.alpha}; κ = ${sci(api.kappa)}). Latency growth over ${int(levels)} levels up to N = ${int(nMax)} is consistent with pure contention, so throughput cannot peak and no separatrix exists.`,
    },
    NOISE: {
      badge: 'INDISTINGUISHABLE FROM NOISE',
      text: `The F-test finds a coherency term (p = ${sci(api.p_value)}), but κ = ${sci(api.kappa)} is only ${ratioText} the instrument's own noise floor (κ = ${sci(floor)}, measured on a no-op target). It cannot be separated from OS scheduler overhead, so it is not reported as a trap.`,
    },
    INSUFFICIENT: {
      badge: 'INSUFFICIENT EVIDENCE',
      text: `Only ${int(levels)} levels were sampled up to N = ${int(nMax)} (minimum ${T.minLevels} levels to N = ${T.minNMax}). Over too narrow a range, a small κ is indistinguishable from zero — a null result here is not evidence of absence. This lens cannot decide.`,
    },
  };
  const alternatives = {
    TRAP: `EVIDENCE OF A TRAP (p < ${T.alpha}, κ > ${T.floorMargin}× NOISE FLOOR)`,
    NONE: `NO EVIDENCE OF A TRAP (p ≥ ${T.alpha})`,
    NOISE: `INDISTINGUISHABLE FROM NOISE (κ < ${T.floorMargin}× FLOOR)`,
    INSUFFICIENT: `INSUFFICIENT EVIDENCE (< ${T.minLevels} LEVELS OR N < ${T.minNMax})`,
  };

  // Meters are scaled so the requirement sits at the midpoint.
  const meter = (value, required) =>
    value === null
      ? {}
      : {
          fillPct: Math.max(0, Math.min(100, (value / (2 * required)) * 100)),
          reqPct: 50,
          req: `minimum ${required}`,
        };

  return {
    outcome,
    levels,
    nMax,
    thresholds: T,
    modelA: {
      label: 'MODEL A — NO COHERENCY COST',
      formula: api.models?.M0?.form ?? 'R(N) = base · (1 + σ(N−1))',
      verdict: verdictA,
      rows: [
        { k: 'free parameters', v: '2 (base, σ)' },
        { k: 'κ (coherency)', v: 'fixed at 0' },
        { k: 'levels sampled', v: int(levels) },
        { k: 'max concurrency', v: `N = ${int(nMax)}` },
      ],
      foot: undecided
        ? 'The measured range is too narrow to choose between the models.'
        : selectedB
          ? 'A monotone capacity curve crosses the offered load exactly once — no trap can exist under this model. The measurements reject it.'
          : 'Latency growth is consistent with pure contention. No trap is possible.',
    },
    modelB: {
      label: 'MODEL B — WITH COHERENCY COST κ',
      formula: api.models?.M1?.form ?? 'R(N) = base · (1 + σ(N−1) + κN(N−1))',
      verdict: verdictB,
      rows: [
        { k: 'free parameters', v: '3 (base, σ, κ)' },
        { k: 'σ (contention)', v: num(api.sigma, 5) },
        { k: 'κ (coherency)', v: sci(api.kappa) },
        { k: 'κ 95% CI', v: ciText },
      ],
      foot: 'The κ term is what produces a peak and therefore a separatrix. Without it, no trap can exist in the model at all.',
    },
    tests: [
      {
        label: 'NESTED F-TEST',
        value: `p = ${sci(api.p_value)}`,
        note: `M1 vs M0, 1 degree of freedom — decides at α = ${T.alpha}`,
      },
      { label: 'κ CONFIDENCE INTERVAL', value: ciText, note: 'bootstrap on relative residuals' },
      {
        label: 'VS INSTRUMENT NOISE FLOOR',
        value: ratioText,
        note:
          floor != null
            ? `floor κ = ${sci(floor)} — measured on a no-op target; ${T.floorMargin}× required`
            : 'no calibration stored — floor unknown',
      },
    ],
    parameters: [
      { name: 'κ — coherency cost', est: sci(api.kappa), ci: ciText, p: sci(api.p_value) },
      { name: 'σ — contention', est: num(api.sigma, 5), ci: '—', p: '—' },
    ],
    adequate: Boolean(api.adequate),
    adequacy: [
      { k: 'LEVELS SAMPLED', v: `${int(levels)}`, ...meter(levels, T.minLevels) },
      { k: 'MAX CONCURRENCY', v: `N = ${int(nMax)}`, ...meter(nMax, T.minNMax) },
      {
        k: 'MEASUREMENT ADEQUATE',
        v: api.adequate ? 'YES' : 'NO — a null result here is not evidence of absence',
      },
      {
        k: 'EXCEEDS NOISE FLOOR',
        v: !api.evidence
          ? 'NOT APPLICABLE — no coherency term detected'
          : api.exceeds_floor === null || api.exceeds_floor === undefined
            ? '— (no calibration stored)'
            : api.exceeds_floor
              ? `YES (${T.floorMargin}× margin)`
              : 'NO — indistinguishable from OS scheduler overhead',
      },
    ],
    goodnessOfFit: {
      modelAR2: num(api.r2, 4),
      usedForVerdict: 'NO',
      runLine: `On this run: R² = ${num(api.r2, 4)}, F-test p = ${sci(api.p_value)} → ${conclusions[outcome].badge.toLowerCase()}.`,
    },
    conclusion: conclusions[outcome],
    alternatives: Object.entries(alternatives)
      .filter(([k]) => k !== outcome)
      .map(([, v]) => v),
  };
}

/* ------------------------------------------------------------------ *
 * BLIND DETECTION
 * ------------------------------------------------------------------ */

export function adaptBlind(api, fallback) {
  const seeds = api?.seeds;
  if (!seeds?.length) return fallback;

  const pct = (v) => `${Math.round((v ?? 0) * 100)}%`;
  const ratio = (a, b) => (b > 0 ? a / b : 0);

  // Totals across EVERY stored seed — the headline claim is about all of
  // them, not whichever one the table happens to show.
  const tot = seeds.reduce(
    (acc, s) => {
      const sc = s.scorecard ?? {};
      acc.tp += sc.tp ?? 0;
      acc.fp += sc.fp ?? 0;
      acc.tn += sc.tn ?? 0;
      acc.fn += sc.fn ?? 0;
      acc.abst += s.abstentions ?? 0;
      return acc;
    },
    { tp: 0, fp: 0, tn: 0, fn: 0, abst: 0 },
  );
  const decided = tot.tp + tot.fp + tot.tn + tot.fn;
  const risky = tot.tp + tot.fn;
  const safe = tot.fp + tot.tn;

  // Order-independence is a CLAIM, so it is computed, not written in: every
  // seed must produce the same scorecard AND the same decision per target.
  // Aliases are reshuffled per seed, so compare by true identity.
  const decisionsBySeed = seeds.map(
    (s) => new Map((s.targets ?? []).map((t) => [t.true_id, Boolean(t.flagged)])),
  );
  const ids = [...decisionsBySeed[0].keys()];
  const flips = ids.filter((id) => decisionsBySeed.some((m) => m.get(id) !== decisionsBySeed[0].get(id)));
  const sameScores = seeds.every((s) =>
    ['tp', 'fp', 'tn', 'fn'].every((k) => (s.scorecard ?? {})[k] === (seeds[0].scorecard ?? {})[k]),
  );
  const seedsAgree = sameScores && flips.length === 0;

  let seedFoot;
  if (seeds.length < 2) {
    seedFoot = 'Only one shuffle stored — order-independence is untested. Store more seeds to check it.';
  } else if (seedsAgree) {
    seedFoot = `Identical outcome under ${seeds.length} independent shuffles — the result is not an artifact of presentation order.`;
  } else {
    seedFoot = `Outcomes DIFFER across shuffles${
      flips.length ? ` (${flips.length} target${flips.length > 1 ? 's' : ''} changed decision)` : ''
    }. The result depends on presentation order and should not be relied on.`;
  }

  // The table and matrix show one seed; say which.
  const shown = seeds[0];
  const sc = shown.scorecard ?? {};

  // Traps: explicit flag from the backend when stored; description match is a
  // fallback for results recorded before the flag existed.
  const isTrap = (t) =>
    typeof t.trap === 'boolean'
      ? t.trap
      : !t.faulty && /must not|borderline|hard negative/i.test(t.why ?? '');

  return {
    shownSeed: shown.seed,
    recordedAt: api.created_at,
    seedsAgree,
    seedFoot,
    confusion: {
      truePositive: sc.tp ?? 0,
      falsePositive: sc.fp ?? 0,
      falseNegative: sc.fn ?? 0,
      trueNegative: sc.tn ?? 0,
    },
    stats: [
      {
        label: 'DETECTION RATE',
        value: pct(ratio(tot.tp, risky)),
        note: `${tot.tp} of ${risky} risky found across ${seeds.length} seeds`,
      },
      {
        label: 'FALSE POSITIVE RATE',
        value: pct(ratio(tot.fp, safe)),
        note: `${tot.fp} of ${safe} safe flagged across ${seeds.length} seeds`,
      },
      {
        label: 'PRECISION',
        value: num(ratio(tot.tp, tot.tp + tot.fp)),
        note:
          tot.fp === 0
            ? 'every refusal was correct'
            : `${tot.fp} refusal${tot.fp > 1 ? 's were' : ' was'} wrong`,
      },
      {
        label: 'ACCURACY',
        value: `${tot.tp + tot.tn} / ${decided}`,
        note:
          tot.abst > 0
            ? `decisions across ${seeds.length} seeds · ${tot.abst} abstained`
            : `decisions across ${seeds.length} seeds`,
      },
    ],
    seeds: seeds.map((s) => {
      const k = s.scorecard ?? {};
      return {
        name: `SEED ${s.seed}`,
        tp: `${k.tp ?? 0}/${(k.tp ?? 0) + (k.fn ?? 0)}`,
        fp: `${k.fp ?? 0}/${(k.fp ?? 0) + (k.tn ?? 0)}`,
        rate: pct(k.detection_rate),
      };
    }),
    targets: (shown.targets ?? []).map((t, i) => {
      // outcome is scored OUTSIDE SYN: OK | MISS | FP | ABST
      const outcome = (t.outcome ?? '').toUpperCase();
      return {
        id: `T-${String(i + 1).padStart(2, '0')}`,
        decision: t.flagged ? 'REFUSE' : 'PASS',
        truth: t.why,
        trap: isTrap(t),
        measure: t.detail,
        outcome,
        correct: outcome === 'OK' ? true : outcome === 'ABST' ? null : false,
      };
    }),
  };
}

/* ------------------------------------------------------------------ *
 * LANDING
 * ------------------------------------------------------------------ */

export function adaptLanding(api, fallback) {
  if (!api?.complexity) return fallback;

  const c = api.complexity;
  const s = api.stability;
  const b = api.blind ?? {};

  const ticker = [
    'n = INPUT SIZE',
    'N = CONCURRENCY',
    `EXPONENT ${num(c.exponent)}`,
    `κ = ${sci(s?.kappa)}`,
    `p = ${sci(s?.p_value)}`,
    s?.peak_throughput ? `PEAK ${int(s.peak_throughput)} rps @ N=${int(s.peak_n)}` : null,
    s?.separatrix ? `SEPARATRIX N=${num(s.separatrix, 1)}` : null,
    `${api.risk === 'refuse' ? 'REFUSED' : (api.risk ?? '').toUpperCase()} WITH GROUNDS`,
  ]
    .filter(Boolean)
    .join(' /// ');

  return {
    ticker: `  ${ticker} ///`,
    bootLines: [
      `> run ${api.commit}................ [OK]`,
      '> probe: complexity(n)........ [OK]',
      '> probe: stability(N)......... [OK]',
      `> scale spread: ${num(c.decades, 1)} oom....... [OK]`,
      `> noise floor: κ=${sci(api.calibration?.kappa_floor, 1)}.. [OK]`,
      `> blind harness: ${b.seeds ?? 0} seeds...... [OK]`,
      `> verdict: ${(api.risk ?? '').toUpperCase()} — with grounds`,
    ],
    stats: [
      {
        label: 'BLIND DETECTION RATE',
        value: `${Math.round((b.detection_rate ?? 0) * 100)}%`,
        note: `${b.tp ?? 0} true positives across ${b.seeds ?? 0} random seeds`,
      },
      {
        label: 'FALSE POSITIVE RATE',
        value: `${Math.round((b.false_positive_rate ?? 0) * 100)}%`,
        note: `${b.tn ?? 0} true negatives, ${b.fp ?? 0} false positives`,
      },
      {
        label: 'COMPLEXITY FAULT',
        value: `≈ ${num(c.exponent, 1)}`,
        note: 'exponent recovered from telemetry',
      },
      {
        label: 'COHERENCY COST',
        value: `p ≈ ${sci(s?.p_value, 0)}`,
        note: `detected on a live service, κ = ${sci(s?.kappa)}`,
      },
    ],
    traps: (api.traps ?? []).map((t, i) => ({
      tag: `TRAP 0${i + 1}`,
      title: t.truth?.split('--')[0]?.trim() ?? t.id,
      body: t.truth ?? '',
      metric: `${t.measure} → ${t.decision}`,
    })),
  };
}
