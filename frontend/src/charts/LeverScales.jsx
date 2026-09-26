/**
 * One-dimensional scales for the two levers. Each marks where the run sits
 * today and the exact values where the gate's answer changes.
 */

const W = 880;
const L = 40;
const R = 840;

function Hatch({ id }) {
  return (
    <defs>
      <pattern id={id} width={8} height={8} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width={8} height={8} fill="#000" />
        <line x1={0} y1={0} x2={0} y2={8} stroke="#2b2b2b" strokeWidth={3} />
      </pattern>
    </defs>
  );
}

/** Exponent axis: PASS ≤ 1.2 < WARN ≤ 1.7 < REFUSED. */
export function ExponentScale({ exponent, ci, probe, thresholds }) {
  const lo = 0.4;
  const hi = 2.6;
  const x = (v) => L + ((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * (R - L);
  const top = 30;
  const h = 34;
  return (
    <svg viewBox={`0 0 ${W} 112`} role="img" aria-label="Growth exponent against the gate thresholds"
      style={{ width: '100%', height: 'auto', display: 'block', fontFamily: "'JetBrains Mono',monospace" }}>
      <Hatch id="an-hatch-exp" />
      <rect x={x(thresholds.refuse)} y={top} width={x(hi) - x(thresholds.refuse)} height={h} fill="url(#an-hatch-exp)" stroke="#fff" />
      <rect x={x(thresholds.warn)} y={top} width={x(thresholds.refuse) - x(thresholds.warn)} height={h} fill="none" stroke="#fff" strokeDasharray="4 3" />
      <rect x={x(lo)} y={top} width={x(thresholds.warn) - x(lo)} height={h} fill="none" stroke="#3d3d3d" />
      <text x={x(lo) + 8} y={top + 21} fontSize={10} fill="#a3a3a3">PASS ≤ {thresholds.warn}</text>
      <text x={(x(thresholds.warn) + x(thresholds.refuse)) / 2} y={top + h + 16} textAnchor="middle" fontSize={10} fill="#fff">WARN</text>
      <text x={x(hi) - 8} y={top + 21} textAnchor="end" fontSize={10} fill="#fff" fontWeight={700}>REFUSED &gt; {thresholds.refuse}</text>
      {[0.5, 1, 2, 2.5].map((t) => (
        <text key={t} x={x(t)} y={top + h + 16} textAnchor="middle" fontSize={10} fill="#5c5c5c">{t}</text>
      ))}
      {ci ? (
        <g>
          <line x1={x(ci[0])} y1={top - 10} x2={x(ci[1])} y2={top - 10} stroke="#fff" strokeWidth={1.2} />
          <line x1={x(ci[0])} y1={top - 14} x2={x(ci[0])} y2={top - 6} stroke="#fff" />
          <line x1={x(ci[1])} y1={top - 14} x2={x(ci[1])} y2={top - 6} stroke="#fff" />
        </g>
      ) : null}
      <line x1={x(exponent)} y1={top - 18} x2={x(exponent)} y2={top + h + 4} stroke="#fff" strokeWidth={2} />
      <text x={x(exponent)} y={top - 22} textAnchor="middle" fontSize={11} fill="#fff" fontWeight={700}>
        MEASURED {exponent.toFixed(2)}
      </text>
      {probe != null && Math.abs(probe - exponent) > 0.005 ? (
        <g>
          <line x1={x(probe)} y1={top} x2={x(probe)} y2={top + h} stroke="#a3a3a3" strokeWidth={1.4} strokeDasharray="2 2" />
          <text x={x(probe)} y={top + h + 30} textAnchor="middle" fontSize={10} fill="#a3a3a3">
            WHAT-IF {probe.toFixed(2)}
          </text>
        </g>
      ) : null}
      <text x={R} y={106} textAnchor="end" fontSize={10} fill="#5c5c5c">e — GROWTH EXPONENT (cost ∝ n^e)</text>
    </svg>
  );
}

/** Coherency cost on a log axis, with the instrument's own noise floor.
 *  Labels are placed on the first row where they overlap nothing already
 *  placed, so marks that sit close together (κ now vs the pass line) stay legible. */
export function KappaScale({ now, lift, pass, floor, margin }) {
  const marks = [now, lift, pass, floor, floor ? floor * margin : null].filter((v) => v > 0);
  const lo = Math.min(...marks) / 2.5;
  const hi = Math.max(...marks) * 2.5;
  const x = (v) => L + ((Math.log10(v) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo))) * (R - L);
  const color = { dim: '#5c5c5c', mid: '#a3a3a3', hi: '#fff' };
  const raw = [
    { v: now, label: 'MEASURED NOW', tone: 'hi' },
    lift && { v: lift, label: 'LIFTS REFUSAL BELOW', tone: 'mid' },
    pass && { v: pass, label: 'PASSES BELOW', tone: 'mid' },
    floor && { v: floor * margin, label: `${margin}× FLOOR — DETECTABLE`, tone: 'dim' },
    floor && { v: floor, label: 'NOISE FLOOR', tone: 'dim' },
  ].filter(Boolean);

  // greedy row assignment; ~6.2 units per character at font-size 10
  const rows = [];
  const placed = raw.map((it) => {
    const text = `${it.label} ${it.v.toExponential(1)}`;
    const w = text.length * 6.2;
    let cx = Math.min(Math.max(x(it.v), L + w / 2), R - w / 2);
    let row = 0;
    while ((rows[row] ?? []).some(([a, b]) => cx - w / 2 < b + 10 && cx + w / 2 > a - 10)) row += 1;
    (rows[row] = rows[row] ?? []).push([cx - w / 2, cx + w / 2]);
    return { ...it, text, cx, row };
  });
  const nRows = Math.max(1, rows.length);
  const axisY = 30 + nRows * 18;
  const height = axisY + 54;

  const decades = [];
  for (let e = Math.ceil(Math.log10(lo)); e <= Math.floor(Math.log10(hi)); e += 1) decades.push(10 ** e);
  return (
    <svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label="Coherency cost kappa: measured, thresholds and noise floor"
      style={{ width: '100%', height: 'auto', display: 'block', fontFamily: "'JetBrains Mono',monospace" }}>
      <Hatch id="an-hatch-kappa" />
      {floor ? (
        <rect x={L} y={axisY - 10} width={Math.max(0, x(floor * margin) - L)} height={20} fill="url(#an-hatch-kappa)" />
      ) : null}
      <line x1={L} y1={axisY} x2={R} y2={axisY} stroke="#3d3d3d" />
      {decades.map((d) => (
        <text key={d} x={x(d)} y={axisY + 30} textAnchor="middle" fontSize={10} fill="#5c5c5c">
          {d.toExponential(0)}
        </text>
      ))}
      {placed.map((it) => {
        const ty = axisY - 22 - it.row * 18;
        return (
          <g key={it.label}>
            <line x1={x(it.v)} y1={axisY - 14} x2={x(it.v)} y2={axisY + 10} stroke={color[it.tone]}
              strokeWidth={it.tone === 'hi' ? 2 : 1.2} strokeDasharray={it.tone === 'dim' ? '2 2' : undefined} />
            <text x={it.cx} y={ty} textAnchor="middle" fontSize={10} fill={color[it.tone]}
              fontWeight={it.tone === 'hi' ? 700 : 400}>
              {it.text}
            </text>
          </g>
        );
      })}
      <text x={R} y={height - 6} textAnchor="end" fontSize={10} fill="#5c5c5c">κ — COHERENCY COST (log)</text>
    </svg>
  );
}
