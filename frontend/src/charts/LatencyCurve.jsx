import {
  AxisCaptions,
  Baseline,
  ChartFrame,
  GridX,
  GridY,
  HatchPattern,
  PLOT,
  fmt,
  logSamples,
  logX,
  logY,
  toPath,
} from './chartMath.jsx';

const SAMPLES = 80;
const HATCH_ID = 'syn-hatch-latency';

const valid = (v) => v !== null && v !== undefined && Number.isFinite(Number(v));

/** Powers of two within [lo, hi] — the natural N axis. */
function pow2Ticks(lo, hi) {
  const out = [];
  for (let v = 1; v <= hi; v *= 2) if (v >= lo) out.push(v);
  return out;
}

/** 1-2-5 ticks across a log range; always at least two. */
function logTicks(lo, hi) {
  const out = [];
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e += 1) {
    for (const m of [1, 2, 5]) {
      const v = m * 10 ** e;
      if (v >= lo && v <= hi) out.push(v);
    }
  }
  const decades = out.filter((v) => Number.isInteger(Math.log10(v)));
  return decades.length >= 2 ? decades : out;
}

/**
 * Latency × N with both fitted models drawn over the same measurements.
 *
 * Model A is fitted INDEPENDENTLY (no κ term), so it chooses its own σ. When κ
 * matters, A tracks the early points and then walks away from the data — it
 * cannot bend upward, so it cannot predict a cliff. When κ does not matter, the
 * two curves coincide, and the chart says so rather than pretending they differ.
 *
 * The y-range is derived from the measurements: flat latency is not squashed
 * into the floor of a fixed 10 ms → 40 s axis.
 */
export default function LatencyCurve({ data }) {
  const { points, separatrix, models, lambda } = data;

  const ns = points.map((p) => p[0]);
  const lats = points.map((p) => p[1]);
  const N_LO = Math.max(1, Math.min(...ns));
  const N_HI = Math.max(...ns);

  // Latency of a model in ms. Live models carry baseMs; fixtures carry λ.
  const responseMs = (m, n) => {
    const base = valid(m.baseMs) ? m.baseMs : 1000 / lambda;
    return base * (1 + m.sigma * (n - 1) + m.kappa * n * (n - 1));
  };

  // y-range from the data, padded; at least one decade so flat data breathes.
  let lo = Math.min(...lats) / 1.4;
  let hi = Math.max(...lats) * 1.6;
  if (hi / lo < 10) {
    const mid = Math.sqrt(lo * hi);
    lo = mid / Math.sqrt(10);
    hi = mid * Math.sqrt(10);
  }
  const LAT_LO = lo;
  const LAT_HI = hi;

  const x = (n) => logX(n, N_LO, N_HI);
  const y = (ms) => logY(Math.max(LAT_LO, Math.min(LAT_HI, ms)), LAT_LO, LAT_HI);

  const measured = points.map(([n, latency]) => ({ n, x: x(n), y: y(latency) }));
  const hasTrap = valid(separatrix);
  const sepX = hasTrap ? x(separatrix) : null;

  const curve = (m) =>
    toPath(logSamples(N_LO, N_HI, SAMPLES).map((n) => [x(n), y(responseMs(m, n))]));

  // Label each curve where it actually ends; merge labels if the curves coincide.
  const endA = y(responseMs(models.a, N_HI));
  const endB = y(responseMs(models.b, N_HI));
  const coincide = Math.abs(endA - endB) < 14;
  const labelA = endA <= endB ? endA - 8 : endA + 16;
  const labelB = endB < endA ? endB - 8 : endB + 16;

  return (
    <ChartFrame title="Latency against concurrency N, with and without a coherency cost term">
      <HatchPattern id={HATCH_ID} />

      <GridY ticks={logTicks(LAT_LO, LAT_HI).map((v) => ({ y: y(v), label: fmt(v) }))} />
      <GridX ticks={pow2Ticks(N_LO, N_HI).map((n) => ({ x: x(n), label: String(n) }))} />
      <Baseline />

      {hasTrap && (
        <rect
          x={sepX}
          y={PLOT.top}
          width={Math.max(0, PLOT.right - sepX)}
          height={PLOT.height}
          fill={`url(#${HATCH_ID})`}
        />
      )}

      <path
        d={curve(models.a)}
        fill="none"
        stroke="#5c5c5c"
        strokeWidth={1.3}
        strokeDasharray="6 4"
      />
      <path d={curve(models.b)} fill="none" stroke="#fff" strokeWidth={1.3} />

      <g>
        {measured.map((p) => (
          <rect key={p.n} x={p.x - 2.5} y={p.y - 2.5} width={5} height={5} fill="#fff" />
        ))}
      </g>

      {coincide ? (
        <text x={PLOT.right - 6} y={Math.min(endA, endB) - 10} textAnchor="end" fontSize={10} fill="#a3a3a3">
          MODELS A AND B COINCIDE — κ ADDS NOTHING
        </text>
      ) : (
        <g>
          <text x={PLOT.right - 6} y={labelA} textAnchor="end" fontSize={10} fill="#7a7a7a">
            MODEL A (κ = 0)
          </text>
          <text x={PLOT.right - 6} y={labelB} textAnchor="end" fontSize={10} fill="#fff">
            MODEL B (κ &gt; 0)
          </text>
        </g>
      )}

      <AxisCaptions x="N — CONCURRENCY (log₂)" y="ms" />
    </ChartFrame>
  );
}
