import {
  AxisCaptions,
  Baseline,
  ChartFrame,
  GridX,
  GridY,
  HatchPattern,
  PLOT,
  fmt,
  linearY,
  logX,
  toPath,
} from './chartMath.jsx';

const HATCH_ID = 'syn-hatch-capacity';

const valid = (v) => v !== null && v !== undefined && Number.isFinite(Number(v));

/** A "nice" linear step (1, 2 or 5 × 10^k) giving roughly `target` ticks. */
function niceStep(range, target = 5) {
  const raw = range / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  return step * mag;
}

function linearTicks(max) {
  const step = niceStep(max);
  const hi = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = 0; v <= hi + step * 1e-6; v += step) ticks.push(Number(v.toFixed(6)));
  return { hi, ticks };
}

/** Powers of two within [lo, hi] — the natural N axis. */
function pow2Ticks(lo, hi) {
  const out = [];
  for (let v = 1; v <= hi; v *= 2) if (v >= lo) out.push(v);
  return out;
}

const one = (v) => (Number.isInteger(v) ? String(v) : Number(v).toFixed(1));

/**
 * Throughput × N.
 *
 * Two shapes are possible, and the chart must render both honestly:
 *   - HUMPED: rise, peak, collapse. A separatrix exists; everything past it is
 *     hatched because the service does not climb out when load is removed.
 *   - MONOTONE: throughput only rises (or saturates). No peak, no separatrix,
 *     no trap is possible. Drawing trap markers here would be a false claim.
 *
 * Both axes are derived from the data — never fixed to one run's scale.
 */
export default function CapacityCurve({ data }) {
  const { points, separatrix, operatingPoint } = data;

  const ns = points.map((p) => p[0]);
  const thr = points.map((p) => p[2]);
  const N_LO = Math.max(1, Math.min(...ns));
  const N_HI = Math.max(...ns);
  const maxThr = Math.max(...thr);
  const { hi: THR_HI, ticks: Y_TICKS } = linearTicks(maxThr * 1.08);

  const x = (n) => logX(n, N_LO, N_HI);
  const y = (t) => linearY(t, 0, THR_HI);

  const measured = points.map(([n, , t]) => ({ n, x: x(n), y: y(t) }));

  // A peak is only a peak if throughput falls after it.
  const peakIdx = thr.indexOf(maxThr);
  const humped = peakIdx < points.length - 1 && thr[thr.length - 1] < maxThr * 0.95;
  const peakN = points[peakIdx][0];
  const peakX = x(peakN);
  const peakY = y(maxThr);

  const hasTrap = humped && valid(separatrix) && valid(operatingPoint);
  const sepX = hasTrap ? x(separatrix) : null;
  const nowX = hasTrap ? x(operatingPoint) : null;
  const headroom = hasTrap ? Number(separatrix) - Number(operatingPoint) : null;

  // Keep the peak callout inside the plot: flip it left near the right edge.
  const BOX_W = 150;
  const boxLeft = peakX + 16 + BOX_W > PLOT.right;
  const boxX = boxLeft ? peakX - 16 - BOX_W : peakX + 16;

  return (
    <ChartFrame
      title={
        humped
          ? `Throughput against concurrency N, peaking at N = ${peakN}`
          : 'Throughput against concurrency N, rising monotonically — no trap possible'
      }
    >
      <HatchPattern id={HATCH_ID} />

      {hasTrap && (
        <rect
          x={sepX}
          y={PLOT.top}
          width={Math.max(0, PLOT.right - sepX)}
          height={PLOT.height}
          fill={`url(#${HATCH_ID})`}
        />
      )}

      <GridY ticks={Y_TICKS.map((t) => ({ y: y(t), label: t === 0 ? '0' : fmt(t) }))} />
      <GridX ticks={pow2Ticks(N_LO, N_HI).map((n) => ({ x: x(n), label: String(n) }))} />
      <Baseline />

      <path
        d={toPath(measured.map((p) => [p.x, p.y]))}
        fill="none"
        stroke="#fff"
        strokeWidth={1.6}
      />
      <g>
        {measured.map((p) => (
          <rect
            key={p.n}
            x={p.x - 2.5}
            y={p.y - 2.5}
            width={5}
            height={5}
            fill="#000"
            stroke="#fff"
            strokeWidth={1.2}
          />
        ))}
      </g>

      {hasTrap && (
        <g>
          {/* separatrix — the line the operating point must never approach */}
          <line
            x1={sepX}
            y1={PLOT.top}
            x2={sepX}
            y2={PLOT.bottom}
            stroke="#fff"
            strokeWidth={1.4}
            strokeDasharray="2 3"
          />
          <line
            x1={nowX}
            y1={PLOT.top}
            x2={nowX}
            y2={PLOT.bottom}
            stroke="#5c5c5c"
            strokeWidth={1}
            strokeDasharray="1 4"
          />
          <line x1={nowX} y1={288} x2={sepX} y2={288} stroke="#7a7a7a" strokeWidth={1} />
          <text x={(nowX + sepX) / 2} y={281} textAnchor="middle" fontSize={10} fill="#a3a3a3">
            HEADROOM {one(headroom)}
          </text>
          <text x={nowX - 7} y={296} textAnchor="end" fontSize={10} fill="#a3a3a3">
            NOW N = {one(Number(operatingPoint))}
          </text>
          <text x={sepX + 10} y={PLOT.top + 14} fontSize={11} fill="#fff">
            SEPARATRIX N = {one(Number(separatrix))}
          </text>
          <text x={sepX + 10} y={PLOT.top + 28} fontSize={10} fill="#a3a3a3">
            TRAPPED BEYOND
          </text>
        </g>
      )}

      {humped ? (
        <g>
          <line
            x1={peakX}
            y1={peakY}
            x2={peakX}
            y2={PLOT.bottom}
            stroke="#fff"
            strokeWidth={1}
            strokeDasharray="1 3"
          />
          <circle cx={peakX} cy={peakY} r={4.5} fill="#fff" />
          <rect
            x={boxX}
            y={peakY + 10}
            width={BOX_W}
            height={34}
            fill="#000"
            stroke="#fff"
            strokeWidth={1}
          />
          <text x={boxX + 10} y={peakY + 24} fontSize={11} fill="#fff">
            PEAK {Math.round(maxThr).toLocaleString('en-US')} rps
          </text>
          <text x={boxX + 10} y={peakY + 37} fontSize={10} fill="#a3a3a3">
            at N = {peakN}
          </text>
        </g>
      ) : (
        <g>
          <rect
            x={PLOT.left + 14}
            y={PLOT.top + 8}
            width={330}
            height={40}
            fill="#000"
            stroke="#3d3d3d"
            strokeWidth={1}
          />
          <text x={PLOT.left + 26} y={PLOT.top + 25} fontSize={11} fill="#fff">
            MONOTONE — NO PEAK, NO SEPARATRIX
          </text>
          <text x={PLOT.left + 26} y={PLOT.top + 39} fontSize={10} fill="#a3a3a3">
            throughput never falls, so no trap can exist
          </text>
        </g>
      )}

      <AxisCaptions x="N — CONCURRENCY (log₂)" y="rps" />
    </ChartFrame>
  );
}
