/**
 * Shared plot geometry.
 *
 * Every chart in SYN is hairline SVG on a fixed 880 × 340 viewBox that scales
 * to its container — precision matters more than texture here, because these
 * plots are the evidence. Axes are drawn by hand so an n-axis (log-log) can
 * never be confused with an N-axis (linear in the measured quantity).
 */

export const GEO = { W: 880, H: 340, L: 62, R: 22, T: 18, B: 40 };

export const PLOT = {
  top: GEO.T,
  bottom: GEO.H - GEO.B,
  left: GEO.L,
  right: GEO.W - GEO.R,
  width: GEO.W - GEO.L - GEO.R,
  height: GEO.H - GEO.T - GEO.B,
};

const span = (v, lo, hi) => (v - lo) / (hi - lo);
const logSpan = (v, lo, hi) => (Math.log(v) - Math.log(lo)) / (Math.log(hi) - Math.log(lo));

/** logarithmic x — the only x scale in this system. */
export const logX = (v, lo, hi) => PLOT.left + logSpan(v, lo, hi) * PLOT.width;

/** linear y — throughput, which has a peak worth reading off directly. */
export const linearY = (v, lo, hi) => PLOT.top + (1 - span(v, lo, hi)) * PLOT.height;

/** logarithmic y — latency and cost, which span orders of magnitude. */
export const logY = (v, lo, hi) => PLOT.top + (1 - logSpan(v, lo, hi)) * PLOT.height;

export const toPath = (points) =>
  points.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');

/** Axis tick formatting: 18630 → 19k, 0.1 → 0.10. */
export function fmt(value) {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k`;
  if (value >= 10) return value.toFixed(0);
  if (value >= 1) return value.toFixed(1);
  return value.toFixed(2);
}

/** Evenly spaced samples across a log range — used to draw fitted curves. */
export function logSamples(lo, hi, steps) {
  const out = [];
  for (let i = 0; i <= steps; i += 1) {
    out.push(Math.exp(Math.log(lo) + (Math.log(hi) - Math.log(lo)) * (i / steps)));
  }
  return out;
}

export function ChartFrame({ children, title }) {
  return (
    <svg
      viewBox={`0 0 ${GEO.W} ${GEO.H}`}
      role="img"
      aria-label={title}
      style={{
        width: '100%',
        height: 'auto',
        display: 'block',
        fontFamily: "'JetBrains Mono',monospace",
        overflow: 'visible',
      }}
    >
      {children}
    </svg>
  );
}

export function Tick({ x, y, anchor, children, fill = '#5c5c5c' }) {
  return (
    <text x={x} y={y} textAnchor={anchor} fontSize={10} fill={fill}>
      {children}
    </text>
  );
}

export function GridX({ ticks }) {
  return (
    <g>
      {ticks.map((tick) => (
        <g key={`gx-${tick.label}`}>
          <line
            x1={tick.x}
            y1={PLOT.top}
            x2={tick.x}
            y2={PLOT.bottom}
            stroke="#131313"
            strokeWidth={1}
          />
          <Tick x={tick.x} y={316} anchor="middle">
            {tick.label}
          </Tick>
        </g>
      ))}
    </g>
  );
}

export function GridY({ ticks }) {
  return (
    <g>
      {ticks.map((tick) => (
        <g key={`gy-${tick.label}`}>
          <line
            x1={PLOT.left}
            y1={tick.y}
            x2={PLOT.right}
            y2={tick.y}
            stroke="#1a1a1a"
            strokeWidth={1}
          />
          <Tick x={PLOT.left - 8} y={tick.y + 4} anchor="end">
            {tick.label}
          </Tick>
        </g>
      ))}
    </g>
  );
}

export function Baseline() {
  return (
    <line
      x1={PLOT.left}
      y1={PLOT.bottom}
      x2={PLOT.right}
      y2={PLOT.bottom}
      stroke="#3d3d3d"
      strokeWidth={1}
    />
  );
}

export function AxisCaptions({ x, y }) {
  return (
    <g>
      <Tick x={PLOT.right} y={334} anchor="end">
        {x}
      </Tick>
      <Tick x={PLOT.left - 46} y={PLOT.top - 4}>
        {y}
      </Tick>
    </g>
  );
}

/** The diagonal hatch that marks a region with no self-recovery. */
export function HatchPattern({ id }) {
  return (
    <defs>
      <pattern
        id={id}
        width={8}
        height={8}
        patternUnits="userSpaceOnUse"
        patternTransform="rotate(45)"
      >
        <rect width={8} height={8} fill="#000" />
        <line x1={0} y1={0} x2={0} y2={8} stroke="#2b2b2b" strokeWidth={3} />
      </pattern>
    </defs>
  );
}
