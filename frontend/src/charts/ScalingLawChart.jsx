import {
  AxisCaptions,
  Baseline,
  ChartFrame,
  GridX,
  GridY,
  PLOT,
  fmt,
  logSamples,
  logX,
  logY,
  toPath,
} from './chartMath.jsx';

const N_LO = 16;
const N_HI = 262144;
const Y_LO = 0.05;
const Y_HI = 3e6;
const X_TICKS = [16, 256, 4096, 65536];
const Y_TICKS = [0.1, 10, 1000, 100000];
const SAMPLES = 60;

/**
 * Cost × n on log-log axes: measurements, the fitted law, its 95% exponent
 * band, and the point where the law crosses a named ceiling.
 *
 * The fitted law is drawn as  cost(n) = floor + c · n^e.  The FLOOR is fixed
 * per-call overhead, visible as the flat region at small n. A pure power law
 * without it dives toward zero at small n and misses the measured points —
 * the exponent is read from the asymptotic tail, where the floor is negligible.
 *
 * Detonation is only drawn for SUPERLINEAR growth. Extrapolating a linear or
 * sublinear law to a ceiling produces a real-looking but meaningless number.
 */
export default function ScalingLawChart({ data }) {
  const { points, law, ceiling, ceilingLabel, superlinear } = data;
  const { coefficient, exponent, exponentLow, exponentHigh, anchor } = law;
  const floor = Number.isFinite(law.floor) ? law.floor : 0;

  const x = (n) => logX(n, N_LO, N_HI);
  const y = (ms) => logY(ms, Y_LO, Y_HI);

  // The band pivots at the anchor so it pinches through the fitted region and
  // fans outward, which is how exponent uncertainty actually behaves.
  const coefficientFor = (e) => coefficient * anchor ** (exponent - e);

  const powerLaw = (a, b) =>
    toPath(
      logSamples(N_LO, N_HI, SAMPLES)
        .map((n) => ({ n, v: floor + a * n ** b }))
        .filter(({ v }) => v >= Y_LO && v <= Y_HI)
        .map(({ n, v }) => [x(n), y(v)]),
    );

  const measured = points.map(([n, cost]) => ({ n, x: x(n), y: y(cost) }));

  // n at which the fitted law reaches the ceiling -- superlinear growth only.
  const detonation =
    superlinear !== false && exponent > 0 && ceiling > floor
      ? ((ceiling - floor) / coefficient) ** (1 / exponent)
      : null;
  const showDetonation =
    detonation !== null && Number.isFinite(detonation) && detonation >= N_LO && detonation <= N_HI;
  const detX = showDetonation ? x(detonation) : null;
  const detY = y(ceiling);

  const sampledLo = points[0][0];
  const sampledHi = points[points.length - 1][0];
  const measX = x(sampledLo);
  const measW = x(sampledHi) - measX;
  const orders = (Math.log10(sampledHi) - Math.log10(sampledLo)).toFixed(1);

  // Keep the detonation callout inside the plot.
  const boxRight = showDetonation && detX - 198 < PLOT.left;
  const boxX = showDetonation ? (boxRight ? detX + 12 : detX - 198) : 0;

  return (
    <ChartFrame title="Resource cost against input size n on log-log axes, with the fitted law">
      <rect x={measX} y={PLOT.top} width={measW} height={PLOT.height} fill="#0c0c0c" />

      <GridY ticks={Y_TICKS.map((v) => ({ y: y(v), label: fmt(v) }))} />
      <GridX ticks={X_TICKS.map((n) => ({ x: x(n), label: fmt(n) }))} />
      <Baseline />

      <path
        d={powerLaw(coefficientFor(exponentLow), exponentLow)}
        fill="none"
        stroke="#3d3d3d"
        strokeWidth={1}
        strokeDasharray="3 3"
      />
      <path
        d={powerLaw(coefficientFor(exponentHigh), exponentHigh)}
        fill="none"
        stroke="#3d3d3d"
        strokeWidth={1}
        strokeDasharray="3 3"
      />
      <path d={powerLaw(coefficient, exponent)} fill="none" stroke="#fff" strokeWidth={1.6} />

      <line
        x1={PLOT.left}
        y1={detY}
        x2={PLOT.right}
        y2={detY}
        stroke="#fff"
        strokeWidth={1.2}
        strokeDasharray="8 4"
      />
      <text x={PLOT.left + 8} y={detY - 8} fontSize={11} fill="#fff">
        {ceilingLabel}
      </text>

      <g>
        {measured.map((p) => (
          <rect
            key={p.n}
            x={p.x - 3}
            y={p.y - 3}
            width={6}
            height={6}
            fill="#000"
            stroke="#fff"
            strokeWidth={1.3}
          />
        ))}
      </g>

      {showDetonation ? (
        <g>
          <line
            x1={detX}
            y1={detY}
            x2={detX}
            y2={PLOT.bottom}
            stroke="#fff"
            strokeWidth={1}
            strokeDasharray="2 3"
          />
          <circle cx={detX} cy={detY} r={6} fill="none" stroke="#fff" strokeWidth={1.6} />
          <circle cx={detX} cy={detY} r={2.4} fill="#fff" />
          <rect x={boxX} y={detY + 16} width={188} height={36} fill="#fff" />
          <text x={boxX + 10} y={detY + 31} fontSize={11} fill="#000" fontWeight={700}>
            DETONATION
          </text>
          <text x={boxX + 10} y={detY + 44} fontSize={10} fill="#000">
            n ≈ {Math.round(detonation).toLocaleString('en-US')} records
          </text>
        </g>
      ) : (
        <text x={PLOT.right - 8} y={detY + 20} textAnchor="end" fontSize={10} fill="#a3a3a3">
          {superlinear === false
            ? 'NOT SUPERLINEAR — NO DETONATION'
            : 'NO CROSSING WITHIN THE PLOTTED RANGE'}
        </text>
      )}

      <text x={measX + 6} y={PLOT.top + 12} fontSize={10} fill="#5c5c5c">
        MEASURED RANGE — {orders} ORDERS OF MAGNITUDE
      </text>

      <AxisCaptions x="n — INPUT SIZE / RECORDS (log₁₀)" y="ms" />
    </ChartFrame>
  );
}
