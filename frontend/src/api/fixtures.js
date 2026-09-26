/**
 * Captured run fixtures.
 *
 * Every number here comes from the run the design was built around:
 * commit 7f3c9a2e1b on feat/order-lookup-batch. They are shaped exactly like
 * the payloads endpoints.js expects from a live gate API, so swapping in a
 * real backend is a matter of setting VITE_API_BASE_URL — nothing in the
 * pages changes.
 */

export const RUN = {
  commit: '7f3c9a2e1b',
  commitShort: '7f3c9a2',
  branch: 'feat/order-lookup-batch',
  timestamp: '2026-09-13T04:12:07Z',
  displayTimestamp: '2026-09-13 04:12:07Z',
  certId: 'syn-7f3c9a2-0412',
  version: 'v0.7.1',
  complexityTarget: 'order_service.order_lookup:41',
  stabilityTarget: 'checkout-api /v2/orders',
};

/* ------------------------------------------------------------------ *
 * LANDING
 * ------------------------------------------------------------------ */

export const LANDING = {
  ticker:
    '  n = INPUT SIZE /// N = CONCURRENCY /// EXPONENT 1.97 /// κ = 6.8e-3 /// p = 1.4e-5 /// PEAK 531 rps @ N=12 /// SEPARATRIX N=104 /// 63× COLLAPSE /// REFUSED WITH GROUNDS ///',
  bootLines: [
    '> loading twin(7f3c9a2)........ [OK]',
    '> order params: 6 dims........ [OK]',
    '> probe: complexity(n)........ [OK]',
    '> probe: stability(N)......... [OK]',
    '> scale spread: 2.4 oom....... [OK]',
    '> blind harness: 9 targets.... [OK]',
    '> verdict: REFUSED — with grounds',
  ],
  stats: [
    {
      label: 'BLIND DETECTION RATE',
      value: '100%',
      note: '3 true positives across 3 random seeds',
    },
    { label: 'FALSE POSITIVE RATE', value: '0%', note: '6 true negatives, 0 false positives' },
    { label: 'COMPLEXITY FAULT', value: '≈ 2.0', note: 'quadratic exponent recovered from telemetry' },
    { label: 'COHERENCY COST', value: 'p ≈ 10⁻⁵', note: 'detected on a live service, κ = 6.8e-3' },
  ],
  traps: [
    {
      tag: 'TRAP 01',
      title: 'O(n log n) merge sort',
      body: 'Superlinear in theory. An exponent threshold set naively fires here every time.',
      metric: 'measured exponent 1.11 → PASS',
    },
    {
      tag: 'TRAP 02',
      title: 'N+1 query pattern',
      body: 'A genuine performance problem — and genuinely linear. Slow is not the same as unsafe to merge.',
      metric: 'measured exponent 1.04 → PASS',
    },
    {
      tag: 'TRAP 03',
      title: 'Pure linear contention',
      body: 'The exact case that defeated an earlier version of the detector: contention with no coherency cost.',
      metric: 'κ = 2.0e-5, p = 0.41 → PASS',
    },
  ],
};

/* ------------------------------------------------------------------ *
 * VERDICT — four states, each with its own evidence
 * ------------------------------------------------------------------ */

export const VERDICT_STATES = ['PASS', 'WARN', 'REFUSED', 'UNKNOWN'];

const PROBE_TIMINGS = [
  { name: 'synthesis.twin_build', seconds: 18.4 },
  { name: 'telemetry.multiscale_sweep', seconds: 42.1 },
  { name: 'complexity.symbolic_regressor', seconds: 96.7 },
  { name: 'stability.capacity_probe', seconds: 134.2 },
  { name: 'stability.lyapunov_cert', seconds: 71.9 },
  { name: 'validation.isomorphism', seconds: 11.3 },
];

const TOTAL_WALL_CLOCK = '374.6 s';

const certificateMeta = (evidence) => [
  { k: 'COMMIT', v: RUN.commit },
  { k: 'BRANCH', v: RUN.branch },
  { k: 'TIMESTAMP', v: RUN.timestamp },
  { k: 'EVIDENCE', v: evidence },
  { k: 'CERT ID', v: RUN.certId },
];

const certificateText = (state, complexityLines, stabilityLines) =>
  [
    'SYN REFUSAL CERTIFICATE',
    '=======================',
    `verdict:   ${state}`,
    `commit:    ${RUN.commit}`,
    `branch:    ${RUN.branch}`,
    `timestamp: ${RUN.timestamp}`,
    '',
    'COMPLEXITY (n = input size)',
    `  target:   ${RUN.complexityTarget}`,
    ...complexityLines,
    '',
    'STABILITY (N = concurrency)',
    `  target:      ${RUN.stabilityTarget}`,
    ...stabilityLines,
    '',
    'These are statistical early warnings with stated p-values, not proofs.',
  ].join('\n');

export const VERDICTS = {
  REFUSED: {
    state: 'REFUSED',
    glyph: '[×]',
    summary:
      'Merge blocked. Two independent probes crossed gate thresholds. The grounds are attached below.',
    evidence: 'COMPLETE — 2 / 2 LENSES',
    findings: [
      {
        probe: 'complexity.scaling_law',
        finding: 'order_lookup grows at exponent 1.97 — superlinear',
        risk: 'HIGH',
      },
      {
        probe: 'complexity.detonation',
        finding: 'fitted law crosses the 30 s gateway timeout at n ≈ 10,548',
        risk: 'HIGH',
      },
      {
        probe: 'stability.capacity',
        finding: 'coherency cost κ = 6.8e-3 (p = 1.4e-5); peak 531 rps at N = 12',
        risk: 'HIGH',
      },
      {
        probe: 'stability.basin',
        finding: '2 stable fixed points; separatrix margin down 61% vs baseline',
        risk: 'HIGH',
      },
      {
        probe: 'complexity.scale_spread',
        finding: '2.4 orders of magnitude sampled (minimum 2.0)',
        risk: 'OK',
      },
      {
        probe: 'validation.isomorphism',
        finding: 'twin residual 4.1% against live telemetry',
        risk: 'LOW',
      },
    ],
    complexity: {
      target: RUN.complexityTarget,
      exponent: '1.97',
      ci: 'CI 95% [1.91, 2.04]',
      superlinearLabel: 'SUPERLINEAR — TRUE',
      superlinear: true,
    },
    stability: [
      { k: 'COHERENCY COST κ', v: '6.8e-3' },
      { k: 'P-VALUE', v: '1.4 × 10⁻⁵' },
      { k: 'PEAK THROUGHPUT', v: '531 rps' },
      { k: 'PEAK AT', v: 'N = 12' },
      { k: 'SEPARATRIX', v: 'N = 104' },
      { k: 'HEADROOM', v: '70 levels (67%)' },
    ],
    remediation: [
      {
        num: '1',
        title: 'Replace the nested scan in order_service.order_lookup:41 with a keyed index.',
        body: 'Drops the measured class from O(n²) to O(n log n). The fitted law then stays below the 30 s gateway timeout across the whole stated envelope, removing the crossing entirely rather than pushing it out.',
      },
      {
        num: '2',
        title:
          'Cap retry_loop.py backoff with decorrelated jitter and open a circuit after 3 consecutive failures.',
        body: 'The second stable fixed point exists because retries are unbounded under load. Bounding them collapses the bistable region to a single healthy basin, so a transient trigger can no longer become self-sustaining.',
      },
      {
        num: '3',
        title: 'Admit at most N = 48 concurrent requests at the edge.',
        body: 'Holds the operating point well below the separatrix at N = 104 while preserving 88% of peak throughput. This is a containment measure, not a fix — it makes the cliff unreachable without removing it.',
      },
    ],
    certificate: certificateMeta('COMPLETE — 2 / 2 LENSES'),
    certificateText: certificateText(
      'REFUSED',
      [
        '  exponent: 1.97  CI95 [1.91, 2.04]  -> superlinear',
        '  law:      cost(n) ~ 3.56e-4 * n^1.97 ms',
        '  crossing: n ~ 10,548 records vs 30s gateway timeout (timeout-bound)',
      ],
      [
        '  kappa:       6.8e-3  CI95 [4.9e-3, 9.1e-3]  p = 1.4e-5',
        '  peak:        531 rps at N = 12',
        '  separatrix:  N = 104',
        '  operating:   N = 34  (headroom 70)',
      ],
    ),
    timings: PROBE_TIMINGS,
    totalWallClock: TOTAL_WALL_CLOCK,
  },

  PASS: {
    state: 'PASS',
    glyph: '[✓]',
    summary:
      'Merge approved. Both lenses returned complete measurements and neither crossed a gate threshold.',
    evidence: 'COMPLETE — 2 / 2 LENSES',
    findings: [
      {
        probe: 'complexity.scaling_law',
        finding: 'order_lookup grows at exponent 1.04 — linear',
        risk: 'LOW',
      },
      {
        probe: 'complexity.detonation',
        finding: 'no ceiling crossing within the stated envelope (n ≤ 10⁶)',
        risk: 'OK',
      },
      {
        probe: 'stability.capacity',
        finding: 'κ = 2.0e-5 (p = 0.41); no peak within N ≤ 256',
        risk: 'LOW',
      },
      { probe: 'stability.basin', finding: '1 stable fixed point; no second basin found', risk: 'OK' },
      {
        probe: 'complexity.scale_spread',
        finding: '2.6 orders of magnitude sampled (minimum 2.0)',
        risk: 'OK',
      },
      {
        probe: 'validation.isomorphism',
        finding: 'twin residual 3.6% against live telemetry',
        risk: 'LOW',
      },
    ],
    complexity: {
      target: RUN.complexityTarget,
      exponent: '1.04',
      ci: 'CI 95% [0.98, 1.11]',
      superlinearLabel: 'SUPERLINEAR — FALSE',
      superlinear: false,
    },
    stability: [
      { k: 'COHERENCY COST κ', v: '2.0e-5' },
      { k: 'P-VALUE', v: '0.41' },
      { k: 'PEAK THROUGHPUT', v: 'none in range' },
      { k: 'PEAK AT', v: '—' },
      { k: 'SEPARATRIX', v: 'none detected' },
      { k: 'HEADROOM', v: 'unbounded in range' },
    ],
    remediation: [],
    certificate: certificateMeta('COMPLETE — 2 / 2 LENSES'),
    certificateText: certificateText(
      'PASS',
      [
        '  exponent: 1.04  CI95 [0.98, 1.11]  -> linear',
        '  crossing: none within the stated envelope (n <= 10^6)',
      ],
      [
        '  kappa:       2.0e-5  p = 0.41  (not distinguishable from zero)',
        '  peak:        none in range',
        '  separatrix:  none detected',
        '  operating:   N = 34  (headroom unbounded in range)',
      ],
    ),
    timings: PROBE_TIMINGS,
    totalWallClock: TOTAL_WALL_CLOCK,
  },

  WARN: {
    state: 'WARN',
    glyph: '[!]',
    summary:
      'Merge allowed with a recorded objection. One threshold was approached but not crossed.',
    evidence: 'COMPLETE — 2 / 2 LENSES',
    findings: [
      {
        probe: 'complexity.scaling_law',
        finding: 'order_lookup grows at exponent 1.28 — superlinear',
        risk: 'MED',
      },
      {
        probe: 'complexity.detonation',
        finding: 'crossing at n ≈ 2.4 × 10⁶, outside the stated envelope',
        risk: 'MED',
      },
      {
        probe: 'stability.capacity',
        finding: 'κ = 9.1e-4 (p = 0.021); peak 812 rps at N = 64',
        risk: 'MED',
      },
      {
        probe: 'stability.basin',
        finding: 'separatrix N = 210; headroom 176 levels (84%)',
        risk: 'LOW',
      },
      {
        probe: 'complexity.scale_spread',
        finding: '2.1 orders of magnitude sampled (minimum 2.0)',
        risk: 'OK',
      },
      {
        probe: 'validation.isomorphism',
        finding: 'twin residual 7.9% — above the 5% advisory bar',
        risk: 'MED',
      },
    ],
    complexity: {
      target: RUN.complexityTarget,
      exponent: '1.28',
      ci: 'CI 95% [1.09, 1.47]',
      superlinearLabel: 'SUPERLINEAR — TRUE',
      superlinear: true,
    },
    stability: [
      { k: 'COHERENCY COST κ', v: '9.1e-4' },
      { k: 'P-VALUE', v: '0.021' },
      { k: 'PEAK THROUGHPUT', v: '812 rps' },
      { k: 'PEAK AT', v: 'N = 64' },
      { k: 'SEPARATRIX', v: 'N = 210' },
      { k: 'HEADROOM', v: '176 levels (84%)' },
    ],
    remediation: [],
    certificate: certificateMeta('COMPLETE — 2 / 2 LENSES'),
    certificateText: certificateText(
      'WARN',
      [
        '  exponent: 1.28  CI95 [1.09, 1.47]  -> superlinear',
        '  crossing: n ~ 2.4e6 records, outside the stated envelope',
      ],
      [
        '  kappa:       9.1e-4  p = 0.021',
        '  peak:        812 rps at N = 64',
        '  separatrix:  N = 210',
        '  operating:   N = 34  (headroom 176)',
      ],
    ),
    timings: PROBE_TIMINGS,
    totalWallClock: TOTAL_WALL_CLOCK,
  },

  UNKNOWN: {
    state: 'UNKNOWN',
    glyph: '[?]',
    summary:
      'SYN could not gather enough evidence to decide. This is not an approval — the gate stays closed until a complete measurement exists.',
    evidence: 'PARTIAL — 0 / 2 LENSES',
    findings: [
      {
        probe: 'complexity.scaling_law',
        finding: 'probe failed — dataset generator exhausted memory at n = 8192',
        risk: 'NONE',
      },
      {
        probe: 'complexity.scale_spread',
        finding: '0.6 orders of magnitude sampled (minimum 2.0)',
        risk: 'NONE',
      },
      {
        probe: 'stability.capacity',
        finding: '3 of 8 required levels completed before the probe window closed',
        risk: 'NONE',
      },
      { probe: 'stability.basin', finding: 'not evaluated — no peak was bracketed', risk: 'NONE' },
      { probe: 'complexity.detonation', finding: 'not evaluated — no law was fitted', risk: 'NONE' },
      {
        probe: 'validation.isomorphism',
        finding: 'twin residual 4.4% against live telemetry',
        risk: 'LOW',
      },
    ],
    complexity: {
      target: RUN.complexityTarget,
      exponent: '——',
      ci: 'NOT ESTIMATED',
      superlinearLabel: 'SUPERLINEAR — CANNOT TELL',
      superlinear: false,
    },
    stability: [
      { k: 'COHERENCY COST κ', v: 'not estimated' },
      { k: 'P-VALUE', v: '—' },
      { k: 'PEAK THROUGHPUT', v: 'not observed' },
      { k: 'PEAK AT', v: '—' },
      { k: 'SEPARATRIX', v: 'cannot be located' },
      { k: 'HEADROOM', v: 'unknown' },
    ],
    remediation: [],
    certificate: certificateMeta('PARTIAL — 0 / 2 LENSES'),
    certificateText: certificateText(
      'UNKNOWN',
      ['  exponent: not estimated', '  crossing: not evaluated — no law was fitted'],
      [
        '  kappa:       not estimated',
        '  peak:        not observed',
        '  separatrix:  cannot be located',
        '  operating:   N = 34  (headroom unknown)',
      ],
    ),
    timings: PROBE_TIMINGS,
    totalWallClock: TOTAL_WALL_CLOCK,
  },
};

/* ------------------------------------------------------------------ *
 * STABILITY — N = concurrency
 * ------------------------------------------------------------------ */

export const STABILITY = {
  target: RUN.stabilityTarget,
  levels: 14,
  secondsPerLevel: 30,
  separatrix: 104,
  operatingPoint: 34,
  peak: { n: 12, throughput: 531 },
  /** lambda — ideal service rate, rps */
  lambda: 89.3,
  /** the two competing fits drawn over the latency measurements */
  models: {
    a: { sigma: 0.14, kappa: 0 },
    b: { sigma: 0.021, kappa: 0.0068 },
  },
  /** [N, latency ms, throughput rps, spread CV %] */
  points: [
    [1, 11.2, 89.3, 0.4],
    [2, 11.8, 169.5, 0.5],
    [4, 13.1, 305.3, 0.7],
    [8, 16.4, 487.8, 1.1],
    [12, 22.6, 531.0, 1.6],
    [16, 34.1, 469.2, 2.4],
    [24, 61.0, 393.4, 3.1],
    [32, 96.8, 330.6, 3.8],
    [48, 178.4, 269.1, 5.2],
    [64, 293.7, 217.9, 6.9],
    [96, 612.0, 156.9, 9.4],
    [128, 1487.0, 86.1, 17.2],
    [192, 4210.0, 45.6, 28.6],
    [256, 30476.0, 8.4, 41.3],
  ],
  stats: [
    { label: 'PEAK THROUGHPUT', value: '531 rps', note: 'at N = 12' },
    { label: 'AT N = 256', value: '8.4 rps', note: '63× decline from peak' },
    { label: 'SEPARATRIX', value: 'N = 104', note: 'no self-recovery beyond' },
    { label: 'HEADROOM', value: '70 levels', note: 'from operating point N = 34' },
  ],
};

/* ------------------------------------------------------------------ *
 * COMPLEXITY — n = input size
 * ------------------------------------------------------------------ */

export const COMPLEXITY = {
  target: RUN.complexityTarget,
  scales: 9,
  /** cost(n) ≈ coefficient · n^exponent ms */
  law: {
    coefficient: 3.56e-4,
    exponent: 1.97,
    exponentLow: 1.91,
    exponentHigh: 2.04,
    /** exponent band pivots here so the band pinches at the sampled centre */
    anchor: 512,
    display: 'cost(n) ≈ 3.56e-4 · n^1.97',
  },
  /** the 30 s gateway timeout the fitted law eventually crosses, in ms */
  ceiling: 30000,
  ceilingLabel: 'CEILING — 30 s GATEWAY TIMEOUT',
  /** [n, cost ms] */
  points: [
    [32, 0.34],
    [64, 1.24],
    [128, 5.31],
    [256, 19.1],
    [512, 79.8],
    [1024, 296],
    [2048, 1204],
    [4096, 4588],
    [8192, 18630],
  ],
  stats: [
    { label: 'GROWTH EXPONENT', value: '1.97', note: 'CI 95% [1.91, 2.04]' },
    { label: 'COMPLEXITY CLASS', value: 'O(n²)', note: 'quadratic — recovered blind' },
    { label: 'DETONATION AT', value: 'n ≈ 10,548', note: 'crosses the 30 s gateway timeout' },
    { label: 'MEASUREMENT RANGE', value: '2.4 oom', note: 'n = 32 → 8192 · minimum 2.0' },
  ],
};

/* ------------------------------------------------------------------ *
 * EVIDENCE — model comparison behind the stability verdict
 * ------------------------------------------------------------------ */

export const EVIDENCE = {
  modelA: {
    label: 'MODEL A — NO COHERENCY COST',
    formula: 'R(N) = (1 + σ(N−1)) / λ',
    verdict: 'REJECTED',
    rows: [
      { k: 'σ (contention)', v: '0.140' },
      { k: 'κ (coherency)', v: 'fixed at 0' },
      { k: 'log-likelihood', v: '−101.7' },
      { k: 'AIC', v: '211.4' },
    ],
    foot: 'Predicts latency at N = 256 as 411 ms. Measured: 30,476 ms. Off by 74×.',
  },
  modelB: {
    label: 'MODEL B — WITH COHERENCY COST κ',
    formula: 'R(N) = (1 + σ(N−1) + κN(N−1)) / λ',
    verdict: 'SELECTED',
    rows: [
      { k: 'σ (contention)', v: '0.021' },
      { k: 'κ (coherency)', v: '6.8 × 10⁻³' },
      { k: 'log-likelihood', v: '−92.1' },
      { k: 'AIC', v: '194.2' },
    ],
    foot: 'The κ term is what produces a peak and therefore a separatrix. Without it, no trap can exist in the model at all.',
  },
  tests: [
    { label: 'LIKELIHOOD-RATIO TEST', value: 'Δ(−2 log L) = 19.1', note: '1 degree of freedom' },
    { label: 'P-VALUE', value: '1.4 × 10⁻⁵', note: 'κ > 0 — the decision criterion' },
    { label: 'ΔAIC (A − B)', value: '+17.2', note: 'B favoured decisively' },
  ],
  parameters: [
    { name: 'κ — coherency cost', est: '6.8 × 10⁻³', ci: '[4.9e-3, 9.1e-3]', p: '1.4 × 10⁻⁵' },
    { name: 'σ — contention', est: '0.021', ci: '[0.009, 0.034]', p: '0.003' },
    { name: 'λ — ideal rate', est: '89.3 rps', ci: '[86.1, 92.6]', p: '—' },
    { name: 'N* — separatrix', est: '104', ci: '[96, 119]', p: '—' },
  ],
  adequacy: [
    {
      k: 'CONCURRENCY LEVELS SAMPLED',
      v: '14',
      req: 'MINIMUM 8 REQUIRED',
      fillPct: 70,
      reqPct: 40,
    },
    { k: 'MAXIMUM N REACHED', v: '256', req: 'MINIMUM N = 64 REQUIRED', fillPct: 100, reqPct: 75 },
    {
      k: 'PEAK BRACKETED WITHIN RANGE',
      v: 'YES — N = 12',
      req: 'PEAK MUST BE BRACKETED',
      fillPct: 100,
      reqPct: 0,
    },
  ],
  goodnessOfFit: {
    modelAR2: '0.981',
    modelAKappaError: '−100%',
  },
};

/* ------------------------------------------------------------------ *
 * BLIND DETECTION — classification without labels
 * ------------------------------------------------------------------ */

export const BLIND_DETECTION = {
  confusion: { truePositive: 3, falsePositive: 0, falseNegative: 0, trueNegative: 6 },
  stats: [
    { label: 'DETECTION RATE', value: '100%', note: '3 of 3 risky found' },
    { label: 'FALSE POSITIVE RATE', value: '0%', note: '0 of 6 safe flagged' },
    { label: 'PRECISION', value: '1.00', note: 'every refusal was correct' },
    { label: 'ACCURACY', value: '9 / 9', note: 'across 3 seeds' },
  ],
  targets: [
    {
      id: 'T-01',
      decision: 'PASS',
      truth: 'hash-map lookup on an indexed key',
      trap: false,
      measure: 'exponent 1.02',
    },
    {
      id: 'T-02',
      decision: 'REFUSE',
      truth: 'nested scan in the report builder',
      trap: false,
      measure: 'exponent 1.97',
    },
    {
      id: 'T-03',
      decision: 'PASS',
      truth: 'merge sort — O(n log n), superlinear in theory',
      trap: true,
      measure: 'exponent 1.11',
    },
    {
      id: 'T-04',
      decision: 'PASS',
      truth: 'paginated fetch with a bounded page',
      trap: false,
      measure: 'exponent 0.99',
    },
    {
      id: 'T-05',
      decision: 'REFUSE',
      truth: 'retry loop with unbounded backoff',
      trap: false,
      measure: 'κ = 6.8e-3, p = 1.4e-5',
    },
    {
      id: 'T-06',
      decision: 'PASS',
      truth: 'N+1 query pattern — real problem, linear',
      trap: true,
      measure: 'exponent 1.04',
    },
    {
      id: 'T-07',
      decision: 'REFUSE',
      truth: 'cache-stampede refill path',
      trap: false,
      measure: 'κ = 4.1e-3, p = 2.7e-4',
    },
    {
      id: 'T-08',
      decision: 'PASS',
      truth: 'pure linear contention — no coherency cost',
      trap: true,
      measure: 'σ = 0.31, κ = 2.0e-5, p = 0.41',
    },
    {
      id: 'T-09',
      decision: 'PASS',
      truth: 'streaming aggregation with constant memory',
      trap: false,
      measure: 'exponent 1.03',
    },
  ],
  seeds: [
    { name: 'SEED 0', tp: '3/3', fp: '0/6', rate: '100%' },
    { name: 'SEED 1', tp: '3/3', fp: '0/6', rate: '100%' },
    { name: 'SEED 2', tp: '3/3', fp: '0/6', rate: '100%' },
  ],
};
