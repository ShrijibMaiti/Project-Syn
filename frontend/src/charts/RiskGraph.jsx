/**
 * The call graph of the code under the gate, laid out in layers by call depth
 * from the HTTP routes. Nodes no route reaches are drawn in a separate band —
 * code that exists but that no request path executes.
 *
 * Styling carries the evidence, never more:
 *   REFUSED  solid white block        WARN     dashed white frame
 *   PASS     white frame              UNKNOWN  hatch
 *   caller of a flagged node (blast radius)   grey block, white rule
 *   NOT MEASURED                               dim frame, dim text
 */

const NW = 188;
const NH = 40;
const GAP = 50;
const VG = 12;
const PAD = 18;
const BAND = 34;

const short = (id) => id.split(':').pop();
const trunc = (s, n) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

function layout(nodes, edges) {
  const preds = new Map(nodes.map((n) => [n.id, []]));
  edges.forEach((e) => preds.get(e.target)?.push(e.source));

  const place = (group) => {
    const layers = new Map();
    group.forEach((n) => {
      if (!layers.has(n.layer)) layers.set(n.layer, []);
      layers.get(n.layer).push(n);
    });
    const keys = [...layers.keys()].sort((a, b) => a - b);
    const index = new Map();
    keys.forEach((k) => {
      const col = layers.get(k);
      col.sort((a, b) => (a.module + a.line).localeCompare(b.module + b.line));
      // barycentre: sit each node near the callers already placed
      const bary = (n) => {
        const ps = preds.get(n.id).filter((p) => index.has(p));
        return ps.length ? ps.reduce((s, p) => s + index.get(p), 0) / ps.length : Infinity;
      };
      col.sort((a, b) => bary(a) - bary(b));
      col.forEach((n, i) => index.set(n.id, i));
    });
    return { layers, keys };
  };

  const reach = place(nodes.filter((n) => n.reachable));
  const rest = place(nodes.filter((n) => !n.reachable));
  const pos = new Map();
  const colHeight = (l) => Math.max(0, ...[...l.layers.values()].map((c) => c.length));
  const hReach = colHeight(reach);
  const hRest = colHeight(rest);

  let top = PAD + (hReach ? BAND : 0);
  reach.keys.forEach((k) =>
    reach.layers.get(k).forEach((n, i) => pos.set(n.id, { x: PAD + k * (NW + GAP), y: top + i * (NH + VG) })));
  const restTop = top + hReach * (NH + VG) + (hReach ? 30 : 0) + (hRest ? BAND : 0);
  rest.keys.forEach((k) =>
    rest.layers.get(k).forEach((n, i) => pos.set(n.id, { x: PAD + k * (NW + GAP), y: restTop + i * (NH + VG) })));

  const maxLayer = Math.max(0, ...nodes.map((n) => n.layer));
  return {
    pos,
    width: PAD * 2 + (maxLayer + 1) * NW + maxLayer * GAP,
    height: restTop + hRest * (NH + VG) + PAD,
    reachTop: PAD,
    restBandY: hRest ? restTop - BAND : null,
    hasReach: hReach > 0,
  };
}

function nodeStyle(status, inBlast) {
  if (status?.risk === 'refuse') return { fill: '#fff', stroke: '#fff', text: '#000', sub: '#3d3d3d' };
  if (status?.risk === 'warn') return { fill: '#000', stroke: '#fff', dash: '5 3', text: '#fff', sub: '#a3a3a3' };
  if (status?.risk === 'ok') return { fill: '#000', stroke: '#fff', text: '#fff', sub: '#a3a3a3' };
  if (status?.risk === 'unknown') return { fill: 'url(#an-hatch-node)', stroke: '#7a7a7a', text: '#fff', sub: '#a3a3a3' };
  if (inBlast) return { fill: '#161616', stroke: '#7a7a7a', text: '#fff', sub: '#a3a3a3', rule: true };
  return { fill: '#000', stroke: '#262626', text: '#7a7a7a', sub: '#4d4d4d' };
}

export default function RiskGraph({ nodes, edges, status, blast, selected, onSelect }) {
  const ids = new Set(nodes.map((n) => n.id));
  const visEdges = edges.filter((e) => ids.has(e.source) && ids.has(e.target));
  const L = layout(nodes, visEdges);
  const flagged = new Set(Object.entries(status).filter(([, s]) => s.risk === 'refuse' || s.risk === 'warn').map(([id]) => id));

  const edgePath = (e) => {
    const a = L.pos.get(e.source);
    const b = L.pos.get(e.target);
    const sx = a.x + NW;
    const sy = a.y + NH / 2;
    if (b.x <= a.x) {
      // same column or backwards: leave and re-enter on the right, bulging into
      // the gap so the curve never crosses a box
      const ex = b.x + NW;
      const ey = b.y + NH / 2;
      const bulge = sx + GAP * 0.55;
      return `M${sx} ${sy} C${bulge} ${sy} ${bulge} ${ey} ${ex + 2} ${ey}`;
    }
    const tx = b.x;
    const ty = b.y + NH / 2;
    const dx = Math.max(30, Math.abs(tx - sx) / 2);
    return `M${sx} ${sy} C${sx + dx} ${sy} ${tx - dx} ${ty} ${tx} ${ty}`;
  };
  const edgeTone = (e) => {
    if (selected && (e.source === selected || e.target === selected)) return { s: '#fff', w: 1.6 };
    if (blast.has(e.source) && (blast.has(e.target) || flagged.has(e.target))) return { s: '#8a8a8a', w: 1.3 };
    return { s: '#262626', w: 1 };
  };

  return (
    <svg
      viewBox={`0 0 ${L.width} ${L.height}`}
      width={L.width}
      height={L.height}
      role="img"
      aria-label="Call graph of the probed code with measured results and blast radius"
      style={{ display: 'block', fontFamily: "'JetBrains Mono',monospace", maxWidth: 'none' }}
    >
      <defs>
        <pattern id="an-hatch-node" width={7} height={7} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width={7} height={7} fill="#000" />
          <line x1={0} y1={0} x2={0} y2={7} stroke="#333" strokeWidth={3} />
        </pattern>
        <marker id="an-arrow" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={6} markerHeight={6} orient="auto-start-reverse">
          <path d="M0 0 L8 4 L0 8 z" fill="#5c5c5c" />
        </marker>
      </defs>

      {L.hasReach ? (
        <text x={PAD} y={L.reachTop + 12} fontSize={10} fill="#7a7a7a" letterSpacing="0.14em">
          REACHED FROM ROUTES — LEFT TO RIGHT BY CALL DEPTH
        </text>
      ) : null}
      {L.restBandY != null ? (
        <g>
          <line x1={PAD} y1={L.restBandY} x2={L.width - PAD} y2={L.restBandY} stroke="#262626" strokeDasharray="4 4" />
          <text x={PAD} y={L.restBandY + 22} fontSize={10} fill="#7a7a7a" letterSpacing="0.14em">
            NOT REACHED FROM ANY ROUTE
          </text>
        </g>
      ) : null}

      <g>
        {visEdges.map((e) => {
          const t = edgeTone(e);
          return (
            <path key={`${e.source}>${e.target}>${e.kind}`} d={edgePath(e)} fill="none" stroke={t.s}
              strokeWidth={t.w} strokeDasharray={e.kind === 'ref' ? '4 3' : undefined} markerEnd="url(#an-arrow)" />
          );
        })}
      </g>

      {nodes.map((n) => {
        const p = L.pos.get(n.id);
        const st = status[n.id];
        const inBlast = blast.has(n.id);
        const s = nodeStyle(st, inBlast);
        const isSel = n.id === selected;
        const sub = n.route
          ? `▸ ${n.route}`
          : st
            ? st.via
              ? `${st.lens} · via ${st.via.split(':').pop()}`
              : `${st.lens} · ${st.metric}`
            : n.module;
        return (
          <g
            key={n.id}
            className="an-graph-node"
            role="button"
            tabIndex={0}
            aria-pressed={isSel}
            aria-label={`${n.id}${st ? `, measured ${st.risk}` : inBlast ? ', in blast radius' : ', not measured'}`}
            onClick={() => onSelect(n.id)}
            onKeyDown={(ev) => {
              if (ev.key === 'Enter' || ev.key === ' ') {
                ev.preventDefault();
                onSelect(n.id);
              }
            }}
            transform={`translate(${p.x} ${p.y})`}
          >
            <title>{n.id}</title>
            {isSel ? <rect x={-5} y={-5} width={NW + 10} height={NH + 10} fill="none" stroke="#fff" strokeDasharray="2 3" /> : null}
            <rect className="an-node-box" width={NW} height={NH} fill={s.fill} stroke={s.stroke} strokeWidth={st ? 1.4 : 1} strokeDasharray={s.dash} />
            {s.rule ? <rect width={3} height={NH} fill="#fff" /> : null}
            <text x={10} y={16} fontSize={11} fill={s.text} fontWeight={st ? 700 : 400}>
              {trunc(short(n.id), 24)}
            </text>
            <text x={10} y={31} fontSize={9} fill={s.sub}>
              {trunc(sub, 30)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
