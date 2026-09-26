import {
  AxisCaptions,
  Baseline,
  ChartFrame,
  GridX,
  GridY,
  HatchPattern,
  PLOT,
  fmt,
  logY,
  toPath,
} from './chartMath.jsx';

const HATCH = 'syn-hatch-headroom';
const linX = (v, lo, hi) => PLOT.left + ((v - lo) / (hi - lo)) * PLOT.width;

function niceTicks(hi, target = 6) {
  const raw = hi / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const n = raw / mag;
  const step = (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * mag;
  const out = [];
  for (let v = 0; v <= hi + step * 1e-9; v += step) out.push(v);
  return out;
}

/**
 * Headroom × offered load, from the run's fitted law.
 *
 * The curve is the gate's own headroom at every load, so the two crossings are
 * exact: left of the WARN line the gate passes, below the REFUSE line it
 * refuses, and past peak capacity no healthy equilibrium exists at all.
 * The x axis is OFFERED LOAD (rps) — neither n nor N.
 */
export default function HeadroomChart({ data, cursorLoad }) {
  const { curve, thresholds, operating_load: now, capacity } = data;
  const xHi = curve[curve.length - 1].load;
  const hs = curve.map((p) => p.headroom).filter((h) => h != null);
  const yLo = 0.5;
  const yHi = Math.min(Math.max(20, ...hs) * 1.3, 2000);
  const x = (v) => linX(v, 0, xHi);
  const y = (h) => logY(Math.max(yLo, Math.min(yHi, h)), yLo, yHi);

  const pts = curve.filter((p) => p.headroom != null).map((p) => [x(p.load), y(p.headroom)]);
  const yTicks = [1, 2, 8, 10, 100, 1000].filter((t) => t >= yLo && t <= yHi);

  const cursor = curve.reduce(
    (best, p) => (Math.abs(p.load - cursorLoad) < Math.abs(best.load - cursorLoad) ? p : best),
    curve[0],
  );
  const capX = x(capacity);

  return (
    <ChartFrame title="Stability headroom against offered load, with the gate's warn and refuse lines">
      <HatchPattern id={HATCH} />

      {/* refused zone: headroom at or below 2 */}
      <rect x={PLOT.left} y={y(2)} width={PLOT.width} height={PLOT.bottom - y(2)} fill={`url(#${HATCH})`} />
      {/* above capacity: no equilibrium exists */}
      <rect x={capX} y={PLOT.top} width={PLOT.right - capX} height={PLOT.height} fill={`url(#${HATCH})`} />

      <GridY ticks={yTicks.map((t) => ({ y: y(t), label: `${fmt(t)}×` }))} />
      <GridX ticks={niceTicks(xHi).map((v) => ({ x: x(v), label: fmt(v) }))} />
      <Baseline />

      <line x1={PLOT.left} y1={y(8)} x2={PLOT.right} y2={y(8)} stroke="#fff" strokeWidth={1} strokeDasharray="6 4" />
      <text x={PLOT.left + 8} y={y(8) - 6} fontSize={10} fill="#a3a3a3">
        WARN LINE — HEADROOM 8×
      </text>
      <line x1={PLOT.left} y1={y(2)} x2={PLOT.right} y2={y(2)} stroke="#fff" strokeWidth={1.2} />
      <text x={PLOT.left + 8} y={y(2) - 6} fontSize={10} fill="#fff">
        REFUSE LINE — HEADROOM 2×
      </text>

      <line x1={capX} y1={PLOT.top} x2={capX} y2={PLOT.bottom} stroke="#fff" strokeWidth={1.2} />
      <text x={capX - 8} y={PLOT.top + 14} textAnchor="end" fontSize={10} fill="#fff">
        PEAK CAPACITY {fmt(capacity)} rps
      </text>
      <text x={capX + 8} y={PLOT.top + 14} fontSize={10} fill="#a3a3a3">
        ABOVE CAPACITY
      </text>

      <path d={toPath(pts)} fill="none" stroke="#fff" strokeWidth={1.8} />

      {/* the two exact crossings */}
      {[
        { L: thresholds.load_ok_max, h: 8, label: `PASS ≤ ${fmt(thresholds.load_ok_max)}` },
        { L: thresholds.load_warn_max, h: 2, label: `REFUSED > ${fmt(thresholds.load_warn_max)}` },
      ].map(({ L, h, label }) => (
        <g key={label}>
          <circle cx={x(L)} cy={y(h)} r={4} fill="#000" stroke="#fff" strokeWidth={1.4} />
          <text x={x(L) - 8} y={y(h) + 16} textAnchor="end" fontSize={10} fill="#fff">
            {label}
          </text>
        </g>
      ))}

      {/* where the service runs today */}
      <line x1={x(now)} y1={PLOT.top} x2={x(now)} y2={PLOT.bottom} stroke="#7a7a7a" strokeWidth={1} strokeDasharray="1 4" />
      <text x={x(now) + 6} y={PLOT.bottom - 8} fontSize={10} fill="#a3a3a3">
        NOW {fmt(now)}
      </text>

      {/* slider cursor */}
      <line x1={x(cursor.load)} y1={PLOT.top} x2={x(cursor.load)} y2={PLOT.bottom} stroke="#fff" strokeWidth={1} strokeDasharray="2 3" />
      {cursor.headroom != null ? (
        <circle cx={x(cursor.load)} cy={y(cursor.headroom)} r={5} fill="#fff" />
      ) : null}

      <AxisCaptions x="λ — OFFERED LOAD (rps, linear)" y="headroom" />
    </ChartFrame>
  );
}
