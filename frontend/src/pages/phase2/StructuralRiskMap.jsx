import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';

import { getRiskMap } from '../../api/analysis.js';
import StatCard from '../../components/StatCard.jsx';
import RiskGraph from '../../charts/RiskGraph.jsx';
import '../../styles/analysis.css';

/**
 * Structural Risk Map — the static call graph of the code under the gate,
 * measured results on the nodes that were measured, and the blast radius of
 * every flagged node.
 *
 * Structure and blast radius are facts about the code (static analysis).
 * Verdicts appear only where a probe measured. Grey means NOT MEASURED — never
 * "safe". What stays written in is method: what the graph can and cannot see.
 */

const LABEL = { ok: 'PASS', warn: 'WARN', refuse: 'REFUSED', unknown: 'UNKNOWN' };
const ok = (v) => v !== null && v !== undefined && Number.isFinite(Number(v));
const short = (id) => (id ? id.split(':').pop() : '—');
const stamp = (epoch) =>
  ok(epoch) ? new Date(epoch * 1000).toISOString().replace('T', ' ').replace(/\.\d+Z$/, 'Z') : '—';

function Verdict({ v }) {
  const key = v || 'unknown';
  return <span className={`an-verdict an-verdict--${key}`}>{LABEL[key] ?? key}</span>;
}

function State({ title, reason, hatch }) {
  return (
    <div className={`an-state${hatch ? ' an-state--hatch' : ''}`}>
      <b>{title}</b>
      <br />
      {reason}
    </div>
  );
}

function NodeList({ ids, onSelect, empty }) {
  if (!ids.length) return <div className="an-list an-list-empty">{empty}</div>;
  return (
    <ul className="an-list">
      {ids.map((id) => (
        <li key={id}>
          <button type="button" onClick={() => onSelect(id)} title={id}>
            {short(id)}
          </button>
        </li>
      ))}
    </ul>
  );
}

export default function StructuralRiskMap() {
  const { search } = useLocation();
  const [res, setRes] = useState({ status: 'loading' });
  const [selected, setSelected] = useState(null);
  const [showIsolated, setShowIsolated] = useState(false);

  useEffect(() => {
    let on = true;
    setRes({ status: 'loading' });
    setSelected(null);
    getRiskMap().then((r) => {
      if (on) setRes(r);
    });
    return () => {
      on = false;
    };
  }, [search]);

  const data = res.status === 'ok' ? res.data : null;

  const derived = useMemo(() => {
    if (!data) return null;
    const { graph, overlay } = data;
    const byId = new Map(graph.nodes.map((n) => [n.id, n]));
    const status = {};
    overlay.items.forEach((it) => {
      if (it.node) status[it.node] = { risk: it.risk, lens: it.lens, metric: it.metric, via: it.via, target: it.target };
    });
    const blast = new Set(overlay.items.flatMap((it) => it.blast_nodes ?? []));
    const callers = new Map(graph.nodes.map((n) => [n.id, []]));
    const callees = new Map(graph.nodes.map((n) => [n.id, []]));
    graph.edges.forEach((e) => {
      callers.get(e.target)?.push(e.source);
      callees.get(e.source)?.push(e.target);
    });
    const degree = (id) => (callers.get(id)?.length ?? 0) + (callees.get(id)?.length ?? 0);
    const visible = graph.nodes.filter(
      (n) => showIsolated || degree(n.id) > 0 || n.route || status[n.id],
    );
    const hidden = graph.nodes.length - visible.length;
    const firstFlagged = overlay.items.find((it) => it.node && (it.risk === 'refuse' || it.risk === 'warn'));
    return { byId, status, blast, callers, callees, visible, hidden, firstFlagged };
  }, [data, showIsolated]);

  useEffect(() => {
    if (derived && !selected) {
      setSelected(derived.firstFlagged?.node ?? derived.visible.find((n) => n.route)?.id ?? derived.visible[0]?.id ?? null);
    }
  }, [derived, selected]);

  const sel = derived && selected ? derived.byId.get(selected) : null;
  const selStatus = sel ? derived.status[sel.id] : null;
  const inBlastOf = sel && data ? data.overlay.items.filter((it) => (it.blast_nodes ?? []).includes(sel.id)) : [];

  return (
    <div className="syn-page">
      <div className="phase2-header">
        <div className="syn-page-kicker">STRUCTURAL RISK MAP — STATIC GRAPH + MEASURED OVERLAY</div>
        <h1 className="syn-page-title">Structural risk map</h1>
        <p className="syn-page-lead syn-page-lead--wide">
          The call graph of the code this run’s manifest points at, built from the source. Measured
          results sit only on the nodes that were measured; everything else is marked NOT MEASURED — SYN
          never invents a margin. The blast radius of a flagged node is every function and HTTP route that
          transitively calls it.
        </p>
        {data ? (
          <div className="syn-page-meta">
            run {data.commit} · verdict {LABEL[data.verdict] ?? data.verdict} · recorded {stamp(data.created_at)} ·
            graph {data.source === 'snapshot' ? 'snapshotted with this run' : 'built from current source'} · packages{' '}
            {data.graph.packages.join(', ')}
          </div>
        ) : null}
      </div>

      {res.status === 'loading' ? <State title="BUILDING THE GRAPH…" reason="Reading this run’s code snapshot." /> : null}
      {res.status === 'unavailable' ? (
        <State
          title="REQUIRES THE LIVE GATE API"
          reason="Set VITE_API_BASE_URL (live API) or VITE_DATA_BASE_URL (CI-published runs). This page has no captured fixture on purpose: a blast radius drawn on an invented graph would be a fabricated risk."
          hatch
        />
      ) : null}
      {res.status === 'error' ? <State title="COULD NOT LOAD THIS RUN" reason={res.message} hatch /> : null}

      {data && derived ? (
        <>
          {data.notes.length ? (
            <div className="an-state an-state--hatch" style={{ marginBottom: 18 }}>
              {data.notes.map((n) => (
                <div key={n}>{n}</div>
              ))}
            </div>
          ) : null}

          <div className="syn-stat-strip">
            <StatCard
              label="FUNCTIONS · METHODS · CLASSES"
              value={data.graph.stats.nodes}
              note={`${data.graph.stats.modules} modules parsed`}
            />
            <StatCard label="RESOLVED CALLS" value={data.graph.stats.edges} note="static — a lower bound" />
            <StatCard
              label="ROUTES IN BLAST RADIUS"
              value={`${data.overlay.stats.routes_affected} / ${data.overlay.stats.routes_total}`}
              note={data.overlay.routes_affected.length ? data.overlay.routes_affected.join(' · ') : 'no route reaches a flagged node'}
            />
            <StatCard
              label="MEASURED COVERAGE"
              value={`${data.overlay.stats.coverage_pct.toFixed(0)}%`}
              note={`${data.overlay.stats.measured_nodes} of ${data.graph.stats.nodes} nodes probed`}
            />
          </div>

          <div className="syn-panel" style={{ marginTop: 24 }}>
            <div className="syn-panel-head">
              <span className="syn-panel-title">CALL GRAPH — {data.graph.packages.join(', ')}</span>
              <span className="an-toggle-row">
                <span className="syn-panel-meta">
                  {derived.hidden ? `${derived.hidden} unconnected nodes hidden` : 'all nodes shown'}
                </span>
                <button
                  type="button"
                  className={`syn-switch${showIsolated ? ' active' : ''}`}
                  aria-pressed={showIsolated}
                  onClick={() => setShowIsolated((v) => !v)}
                >
                  {showIsolated ? 'HIDE UNCONNECTED' : 'SHOW ALL'}
                </button>
              </span>
            </div>
            <div className="an-graph-scroll">
              <RiskGraph
                nodes={derived.visible}
                edges={data.graph.edges}
                status={derived.status}
                blast={derived.blast}
                selected={selected}
                onSelect={setSelected}
              />
            </div>
            <div className="syn-legend">
              <span className="syn-legend-item"><span className="an-verdict an-verdict--refuse">REFUSED</span></span>
              <span className="syn-legend-item"><span className="an-verdict an-verdict--warn">WARN</span></span>
              <span className="syn-legend-item"><span className="an-verdict an-verdict--ok">PASS</span></span>
              <span className="syn-legend-item"><span className="an-verdict an-verdict--unknown">UNKNOWN</span></span>
              <span className="syn-legend-item">▌ CALLS A FLAGGED NODE (BLAST RADIUS)</span>
              <span className="syn-legend-item">▢ NOT MEASURED</span>
              <span className="syn-legend-item">▸ HTTP ROUTE</span>
              <span className="syn-legend-item">- - - CALLABLE PASSED AS ARGUMENT</span>
            </div>
          </div>

          {sel ? (
            <div className="an-detail">
              <div className="an-detail-panel">
                <div className="an-lever-kicker">SELECTED NODE · {sel.kind.toUpperCase()}</div>
                <div className="an-detail-title">{short(sel.id)}</div>
                <div className="an-detail-sub">
                  {sel.module} · {sel.file}:{sel.line}
                  {sel.route ? ` · ▸ ${sel.route}` : ''}
                </div>
                {selStatus ? (
                  <div className="syn-kv">
                    <span className="syn-kv-k">
                      measured · {selStatus.lens} · {selStatus.target}
                    </span>
                    <span className="syn-kv-v">
                      <Verdict v={selStatus.risk} /> {selStatus.metric}
                    </span>
                  </div>
                ) : (
                  <div className="an-lever-body">
                    Not measured. No probe was declared for this code, so SYN makes no claim about it —
                    grey is the absence of evidence, not a pass.
                  </div>
                )}
                {selStatus?.via ? (
                  <div className="an-lever-body" style={{ marginTop: 8 }}>
                    Measured through the instance <b>{short(selStatus.via)}</b>. Calls made through other
                    instances of this class are not covered by that result.
                  </div>
                ) : null}
                {inBlastOf.length ? (
                  <div className="an-callout">
                    In the blast radius of {inBlastOf.map((it) => `${it.target} (${LABEL[it.risk]})`).join(', ')}: this code
                    calls, directly or transitively, a node the gate flagged.
                  </div>
                ) : null}
              </div>
              <div className="an-detail-panel">
                <div className="an-subhead">CALLED BY ({derived.callers.get(sel.id)?.length ?? 0})</div>
                <NodeList ids={derived.callers.get(sel.id) ?? []} onSelect={setSelected} empty="no resolved callers" />
                <div className="an-subhead">CALLS ({derived.callees.get(sel.id)?.length ?? 0})</div>
                <NodeList ids={derived.callees.get(sel.id) ?? []} onSelect={setSelected} empty="no resolved calls" />
              </div>
            </div>
          ) : null}

          <div className="syn-section-head" style={{ margin: '34px 0 14px' }}>
            <span className="syn-section-marker">▤</span>
            <span className="syn-section-kicker">WHERE EACH MEASUREMENT LANDS</span>
            <span className="syn-section-rule" />
          </div>
          <div className="syn-panel">
            {data.overlay.items.map((it) => (
              <div className="an-probe-row" key={`${it.lens}-${it.target}`}>
                <div>
                  <div>{it.lens} · {it.target}</div>
                  <div style={{ color: 'var(--syn-text-dim)', wordBreak: 'break-all' }}>{it.ref ?? '—'}</div>
                </div>
                <div>
                  {it.node ? (
                    <>
                      <button type="button" className="syn-switch" onClick={() => setSelected(it.node)}>
                        {short(it.node)}
                      </button>{' '}
                      <span style={{ color: 'var(--syn-text-secondary)' }}>{it.metric}</span>
                      <div style={{ marginTop: 6, color: 'var(--syn-text-secondary)' }}>
                        routes that reach it: {it.reaching_routes?.length ? it.reaching_routes.join(' · ') : 'none'}
                      </div>
                      {!it.reaching_routes?.length ? (
                        <div className="an-callout">
                          No route calls this code. The result applies to code that no request path
                          executes — worth checking that the code you measured is the code you ship.
                        </div>
                      ) : null}
                      {it.blast_routes?.length ? (
                        <div className="an-callout">
                          Blast radius: {it.blast_nodes.length} callers, {it.blast_routes.length} route
                          {it.blast_routes.length > 1 ? 's' : ''} ({it.blast_routes.join(' · ')}).
                        </div>
                      ) : null}
                    </>
                  ) : (
                    <span style={{ color: 'var(--syn-text-secondary)' }}>not placed on the graph — {it.reason}</span>
                  )}
                </div>
                <div className="syn-align-right">
                  <Verdict v={it.risk} />
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}

      <div className="an-notes">
        <div className="an-note">
          <div className="an-note-label">WHAT THE GRAPH CAN AND CANNOT SEE</div>
          <div className="an-note-body">
            <ul>
              <li>Built by static analysis of the source: imports, direct calls, method calls through module-level instances, and callables passed as arguments.</li>
              <li>Calls through getattr, dynamic dispatch, dependency injection or string lookups are invisible, so every blast radius is a lower bound.</li>
              <li>Two instances of one class share a method node, but each edge records which instance it went through — a probe of one never vouches for callers of the other.</li>
              <li>Each run snapshots the graph when it is stored, so the map shows that run’s code, not today’s.</li>
            </ul>
          </div>
        </div>
        <div className="an-note an-note--roadmap">
          <div className="an-note-label">NOT BUILT — PER-NODE STABILITY WELLS</div>
          <div className="an-note-body">
            The original concept drew every node as a well whose depth is its stability margin. That needs
            a measured margin per node, which means choosing what to probe automatically — the one thing
            the blind-detection result explicitly does not validate. Until then, grey nodes stay grey.
          </div>
        </div>
      </div>
    </div>
  );
}
