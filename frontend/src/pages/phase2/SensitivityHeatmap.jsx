import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';

import { getSensitivity } from '../../api/analysis.js';
import AxisLabel from '../../components/AxisLabel.jsx';
import StatCard from '../../components/StatCard.jsx';
import HeadroomChart from '../../charts/HeadroomChart.jsx';
import { ExponentScale, KappaScale } from '../../charts/LeverScales.jsx';
import '../../styles/analysis.css';

/**
 * Sensitivity — what would flip this verdict.
 *
 * Every number on this page is computed by the backend from the laws the run
 * fitted, with the gate's own decision rule (verified by tests/check_18).
 * What stays written in is METHOD: how the numbers are made, and what this page
 * is not.
 */

const LABEL = { ok: 'PASS', warn: 'WARN', refuse: 'REFUSED', unknown: 'UNKNOWN' };
const CEILINGS = [1, 5, 30, 60];

const ok = (v) => v !== null && v !== undefined && Number.isFinite(Number(v));
const f = (v, d = 0) => (ok(v) ? Number(v).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }) : '—');
const sci = (v, d = 2) => (ok(v) ? Number(v).toExponential(d) : '—');
const pct = (v) => (ok(v) ? `${Math.abs(v).toFixed(0)}%` : '—');
const big = (v) => {
  if (!ok(v)) return '—';
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)} billion`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} million`;
  return Math.round(v).toLocaleString('en-US');
};
const stamp = (epoch) =>
  ok(epoch) ? new Date(epoch * 1000).toISOString().replace('T', ' ').replace(/\.\d+Z$/, 'Z') : '—';

function Verdict({ v }) {
  const key = v || 'unknown';
  return <span className={`an-verdict an-verdict--${key}`}>{LABEL[key] ?? key}</span>;
}

const lensOf = (key) => {
  const [lens, ...rest] = key.split(':');
  return { lens, target: rest.join(':') };
};

/** The concrete change that moves one lens to `to`, in the run's own numbers. */
function leverFor(key, to, data) {
  const { lens, target } = lensOf(key);
  if (lens === 'stability') {
    const s = data.stability.find((x) => x.target === target);
    if (!s || s.mode !== 'trap_model') return 'measure adequately first';
    const goal = to === 'ok' ? 'to_pass' : 'to_lift_refusal';
    const k = s.levers.kappa[goal];
    const L = s.levers.load[goal];
    const parts = [];
    if (k && !k.already) parts.push(`κ ≤ ${sci(k.kappa)} (−${pct(k.reduction_pct)})`);
    if (L) parts.push(`or offered load ≤ ${f(L.load)} rps (−${pct(L.reduction_pct)})`);
    parts.push(`or cap in-flight at N ≤ ${s.levers.concurrency_cap.cap_n}`);
    return parts.join(' ');
  }
  const c = data.complexity.find((x) => x.target === target);
  if (!c || c.mode !== 'law') return 'measure adequately first';
  const t = to === 'ok' ? c.thresholds.warn : c.thresholds.refuse;
  return `exponent ≤ ${t} — 10× the records may cost at most ${f(10 ** t)}× the time (today ${f(c.scale_10x)}×)`;
}

function PlanRow({ label, step, data }) {
  return (
    <div className="an-plan-row">
      <div className="an-plan-k">{label}</div>
      <div className="an-plan-v">
        {step.changes.map((c) => (
          <div className="an-plan-step" key={c.lens}>
            <span className="an-plan-step-lens">
              {c.lens.replace(':', ' · ')} <Verdict v={c.from} /> → <Verdict v={c.to} />
            </span>
            <span className="an-plan-step-how">{leverFor(c.lens, c.to, data)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Plan({ data }) {
  const p = data.plan;
  if (!p) return null;
  const lift = p.to_lift_refusal;
  const needsPass = lift?.changes.some((c) => c.to === 'ok') && lift.changes.length > 1;
  return (
    <div className="an-plan">
      <div className="an-plan-row">
        <div className="an-plan-k">VERDICT NOW</div>
        <div className="an-plan-v">
          <Verdict v={p.current} />
          {p.current === 'ok' ? (
            <span style={{ marginLeft: 12 }}>
              Nothing to change: every lens passes. The margins below show how far each could drift
              before the answer changes.
            </span>
          ) : null}
        </div>
      </div>
      {lift ? <PlanRow label="TO LIFT THE REFUSAL" step={lift} data={data} /> : null}
      {p.to_pass ? <PlanRow label="TO PASS" step={p.to_pass} data={data} /> : null}
      {!p.to_pass && p.blocked_by_unknown.length ? (
        <div className="an-plan-row">
          <div className="an-plan-k">TO PASS</div>
          <div className="an-plan-v">
            Unreachable by any lever: {p.blocked_by_unknown.map((b) => b.replace(':', ' · ')).join(', ')}{' '}
            could not decide. A measurement that could not decide has no counterfactual — widen the
            sweep and re-run first.
          </div>
        </div>
      ) : null}
      {needsPass || p.current === 'refuse' ? (
        <div className="an-plan-row">
          <div className="an-plan-k">WHY THIS COMBINATION</div>
          <div className="an-plan-v an-plan-foot">
            {p.escalation_note} Each lens has several levers; any one of those listed moves it.
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ModeState({ title, reason, hatch }) {
  return (
    <div className={`an-state${hatch ? ' an-state--hatch' : ''}`}>
      <b>{title}</b>
      <br />
      {reason}
    </div>
  );
}

function StabilityBlock({ s }) {
  const curve = s.curve ?? [];
  const nowIdx = useMemo(
    () =>
      curve.reduce(
        (best, p, i) =>
          Math.abs(p.load - s.operating_load) < Math.abs(curve[best].load - s.operating_load) ? i : best,
        0,
      ),
    [curve, s.operating_load],
  );
  const [idx, setIdx] = useState(nowIdx);
  useEffect(() => setIdx(nowIdx), [nowIdx]);

  if (s.mode !== 'trap_model') {
    const titles = {
      inadequate: 'NO COUNTERFACTUAL — THE MEASUREMENT COULD NOT DECIDE',
      no_coherency: 'NO CLIFF TO MOVE AWAY FROM',
      below_floor: 'INSIDE THE INSTRUMENT’S NOISE FLOOR',
      missing: 'LAW NOT STORED WITH THIS RUN',
    };
    return <ModeState title={titles[s.mode] ?? s.mode.toUpperCase()} reason={s.reason} hatch={s.mode === 'inadequate'} />;
  }

  const cur = curve[Math.min(idx, curve.length - 1)];
  const now = s.now;
  const L = s.levers;
  const th = s.thresholds;
  const kLift = L.kappa.to_lift_refusal;
  const kPass = L.kappa.to_pass;
  const cap = L.concurrency_cap;
  const el = s.elasticity;
  const underFloor = [kLift, kPass].some((k) => k && k.below_floor_margin);

  return (
    <div>
      <div className="syn-panel">
        <div className="syn-panel-head">
          <span className="syn-panel-title">HEADROOM × OFFERED LOAD — {s.target}</span>
          <span className="syn-panel-meta">
            GATE PASSES ≤ {f(th.load_ok_max)} rps · REFUSES &gt; {f(th.load_warn_max)} rps
          </span>
        </div>
        <div className="syn-chart-body">
          <HeadroomChart data={s} cursorLoad={cur.load} />
        </div>
        <div className="an-slider-row">
          <div className="an-slider-cell">
            <div className="an-slider-label">WHAT IF THE OFFERED LOAD WERE…</div>
            <input
              className="an-range"
              type="range"
              min={0}
              max={curve.length - 1}
              value={idx}
              onChange={(e) => setIdx(Number(e.target.value))}
              aria-label="Offered load"
            />
            <div className="an-range-scale">
              <span>{f(curve[0].load)} rps</span>
              <button type="button" className="syn-switch" onClick={() => setIdx(nowIdx)}>
                RESET TO TODAY ({f(s.operating_load)} rps)
              </button>
              <span>{f(curve[curve.length - 1].load)} rps</span>
            </div>
          </div>
          <div className="an-readout">
            <div className="an-readout-head">
              <span className="an-readout-value">{f(cur.load)} rps</span>
              <Verdict v={cur.verdict} />
            </div>
            {cur.region === 'bistable' ? (
              <div className="syn-kv">
                <span className="syn-kv-k">healthy N → cliff N</span>
                <span className="syn-kv-v">
                  {f(cur.healthy_n, 1)} → {f(cur.separatrix, 1)} · headroom {f(cur.headroom, 2)}×
                </span>
              </div>
            ) : (
              <div className="an-lever-body">
                {cur.region === 'above_capacity'
                  ? 'Above peak capacity: no healthy equilibrium exists — the queue can only grow.'
                  : 'No separatrix at this load: the cliff is out of reach.'}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="syn-stat-strip">
        <StatCard
          label="HEADROOM NOW"
          value={ok(now.headroom) ? `${f(now.headroom, 2)}×` : '—'}
          note={`${LABEL[now.verdict]} at ${f(s.operating_load)} rps · N ${f(now.healthy_n, 1)} → cliff at ${f(now.separatrix, 1)}`}
        />
        <StatCard
          label="LOAD FOR PASS"
          value={`≤ ${f(th.load_ok_max)} rps`}
          note={L.load.to_pass ? `${pct(L.load.to_pass.reduction_pct)} below today` : 'already passes'}
        />
        <StatCard
          label="LOAD TO LIFT A REFUSAL"
          value={`≤ ${f(th.load_warn_max)} rps`}
          note={L.load.to_lift_refusal ? `${pct(L.load.to_lift_refusal.reduction_pct)} below today` : 'not refused today'}
        />
        <StatCard
          label="PEAK CAPACITY"
          value={`${f(s.capacity)} rps`}
          note={`at N ≈ ${f(s.peak_n, 1)} — above it, collapse is certain`}
        />
      </div>

      <div className="an-levers">
        <div className={`an-lever${kPass && !kPass.already ? ' an-lever--lit' : ''}`}>
          <div className="an-lever-kicker">LEVER · REDUCE COHERENCY COST κ</div>
          <div className="an-lever-value">
            {kPass?.already ? 'already passes' : `κ ≤ ${sci(kPass?.kappa)} to pass`}
          </div>
          <div className="an-lever-body">
            Today κ = {sci(s.kappa)}.{' '}
            {kLift && !kLift.already
              ? `Lifting the refusal needs κ ≤ ${sci(kLift.kappa)} (−${pct(kLift.reduction_pct)}). `
              : ''}
            {kPass && !kPass.already ? `Passing needs κ ≤ ${sci(kPass.kappa)} (−${pct(kPass.reduction_pct)}). ` : ''}
            Base latency and σ held at their fitted values.
            {underFloor
              ? ` At that level κ would sit within ${s.floor_margin}× of the instrument’s own noise floor — the gate would read it as OS overhead rather than measure it.`
              : ''}
          </div>
        </div>

        <div className="an-lever">
          <div className="an-lever-kicker">LEVER · CAP CONCURRENCY</div>
          <div className="an-lever-value">in-flight N ≤ {cap.cap_n}</div>
          <div className="an-lever-body">
            An admission limit at the throughput peak keeps the service at {f(cap.throughput_at_cap)} rps and
            makes the collapse branch unreachable: load beyond capacity waits in a queue instead of
            entering the service and spiralling. Today the cliff sits at N = {f(cap.separatrix_now, 1)}.
            This changes no code — it changes what the gate is protecting against.
          </div>
        </div>

        <div className="an-lever">
          <div className="an-lever-kicker">SENSITIVITY AT TODAY’S LOAD</div>
          <div className="an-lever-value">
            {ok(el.headroom_per_load) ? `1% load → ${f(-el.headroom_per_load, 1)}% headroom lost` : '—'}
          </div>
          <div className="an-lever-body">
            Elasticity of headroom: a 1% rise in offered load removes{' '}
            {ok(el.headroom_per_load) ? `${f(-el.headroom_per_load, 1)}%` : '—'} of it; a 1% rise in κ removes{' '}
            {ok(el.headroom_per_kappa) ? `${f(-el.headroom_per_kappa, 1)}%` : '—'}. The larger the number, the
            closer this verdict sits to a knife edge.
          </div>
        </div>
      </div>

      <div className="syn-panel" style={{ marginTop: 18 }}>
        <div className="syn-panel-head">
          <span className="syn-panel-title">COHERENCY COST κ — WHERE THE GATE CHANGES ITS ANSWER</span>
          <span className="syn-panel-meta">HATCHED: WITHIN {s.floor_margin}× OF THE INSTRUMENT’S OWN NOISE</span>
        </div>
        <div className="syn-chart-body">
          <KappaScale
            now={s.kappa}
            lift={kLift && !kLift.already ? kLift.kappa : null}
            pass={kPass && !kPass.already ? kPass.kappa : null}
            floor={s.kappa_floor}
            margin={s.floor_margin}
          />
        </div>
      </div>
    </div>
  );
}

function ComplexityBlock({ c, ceilingS, onCeiling }) {
  const [probe, setProbe] = useState(c.exponent ?? 1);
  useEffect(() => setProbe(c.exponent ?? 1), [c.exponent]);

  if (c.mode !== 'law') {
    return <ModeState title="NO COUNTERFACTUAL — NO EXPONENT WAS RECOVERED" reason={c.reason} hatch />;
  }
  const th = c.thresholds;
  const lensAt = (e) => (e > th.refuse ? 'refuse' : e > th.warn ? 'warn' : 'ok');
  const crossAt = (e) =>
    c.anchor?.n && e > 0 && c.anchor.cost_s < ceilingS ? c.anchor.n * (ceilingS / c.anchor.cost_s) ** (1 / e) : null;
  const cc = c.ceiling_crossing;
  const m = c.margins;
  const next =
    c.lens_from_exponent === 'ok'
      ? `${f(m.to_warn_line, 2)} below the WARN line`
      : c.lens_from_exponent === 'warn'
        ? `${f(m.to_refuse_line, 2)} below the REFUSE line, ${f(-m.to_warn_line, 2)} above WARN`
        : `${f(-m.to_refuse_line, 2)} above the REFUSE line`;

  return (
    <div>
      <div className="syn-panel">
        <div className="syn-panel-head">
          <span className="syn-panel-title">GROWTH EXPONENT AGAINST THE GATE — {c.target}</span>
          <span className="syn-panel-meta">
            {c.exponent_ci ? `95% CI [${f(c.exponent_ci[0], 2)}, ${f(c.exponent_ci[1], 2)}]` : 'tail-slope estimate'}
          </span>
        </div>
        <div className="syn-chart-body">
          <ExponentScale exponent={c.exponent} ci={c.exponent_ci} probe={probe} thresholds={th} />
        </div>
        <div className="an-slider-row">
          <div className="an-slider-cell">
            <div className="an-slider-label">WHAT IF THE GROWTH EXPONENT WERE…</div>
            <input
              className="an-range"
              type="range"
              min={0.8}
              max={2.6}
              step={0.01}
              value={probe}
              onChange={(e) => setProbe(Number(e.target.value))}
              aria-label="Growth exponent"
            />
            <div className="an-range-scale">
              <span>0.8</span>
              <button type="button" className="syn-switch" onClick={() => setProbe(c.exponent)}>
                RESET TO MEASURED ({f(c.exponent, 2)})
              </button>
              <span>2.6</span>
            </div>
          </div>
          <div className="an-readout">
            <div className="an-readout-head">
              <span className="an-readout-value">e = {f(probe, 2)}</span>
              <Verdict v={lensAt(probe)} />
            </div>
            <div className="syn-kv">
              <span className="syn-kv-k">10× the records</span>
              <span className="syn-kv-v">{f(10 ** probe)}× the time</span>
            </div>
            <div className="syn-kv">
              <span className="syn-kv-k">reaches {ceilingS} s at</span>
              <span className="syn-kv-v">{probe > th.warn ? `n ≈ ${big(crossAt(probe))}` : 'not predicted (not superlinear)'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="syn-stat-strip">
        <StatCard
          label="10× RECORDS COSTS"
          value={`${f(c.scale_10x)}× time`}
          note={c.scale_10x_ci ? `CI ${f(c.scale_10x_ci[0])}× – ${f(c.scale_10x_ci[1])}×` : 'from the tail exponent'}
        />
        <StatCard label="MARGIN" value={`${f(c.exponent, 2)}`} note={next} />
        <StatCard
          label="LEVER TO PASS"
          value={c.levers.to_pass ? `exponent ≤ ${th.warn}` : 'none needed'}
          note={c.levers.to_pass ? `10× records ≤ ${f(c.levers.to_pass.scale_10x)}× time` : 'already below the WARN line'}
        />
        <StatCard
          label={`CROSSES ${ceilingS} s AT`}
          value={cc.gated && ok(cc.n) ? `n ≈ ${big(cc.n)}` : 'none'}
          note={
            cc.gated && cc.n_ci
              ? `CI n ≈ ${big(cc.n_ci[0])} – ${big(cc.n_ci[1])}, from n = ${big(c.anchor.n)}`
              : 'not superlinear — the gate predicts no crossing'
          }
        />
      </div>

      <div className="an-toggle-row" style={{ marginTop: 14 }}>
        <span className="syn-switch-label">CEILING</span>
        {CEILINGS.map((s) => (
          <button
            key={s}
            type="button"
            className={`syn-switch${s === ceilingS ? ' active' : ''}`}
            aria-pressed={s === ceilingS}
            onClick={() => onCeiling(s)}
          >
            {s} s
          </button>
        ))}
      </div>
    </div>
  );
}

export default function SensitivityHeatmap() {
  const { search } = useLocation();
  const [ceilingS, setCeilingS] = useState(30);
  const [res, setRes] = useState({ status: 'loading' });

  useEffect(() => {
    let on = true;
    setRes((r) => (r.status === 'ok' ? r : { status: 'loading' }));
    getSensitivity(ceilingS).then((r) => {
      if (on) setRes(r);
    });
    return () => {
      on = false;
    };
  }, [search, ceilingS]);

  const data = res.status === 'ok' ? res.data : null;

  return (
    <div className="syn-page">
      <div className="phase2-header">
        <div className="syn-page-kicker">SENSITIVITY — WHAT WOULD FLIP THIS VERDICT</div>
        <h1 className="syn-page-title">What it would take</h1>
        <p className="syn-page-lead syn-page-lead--wide">
          A refusal says no. This page says what would make it yes: the smallest change to each measured
          quantity that moves the verdict across a gate line, computed exactly from the laws this run
          fitted, with the gate’s own decision rule. Every threshold below is the point where the real
          gate changes its answer.
        </p>
        {data ? (
          <div className="syn-page-meta">
            run {data.commit} · verdict {LABEL[data.verdict] ?? data.verdict} · recorded {stamp(data.created_at)}
          </div>
        ) : null}
      </div>

      {res.status === 'loading' ? <ModeState title="COMPUTING COUNTERFACTUALS…" reason="Reading the fitted laws for this run." /> : null}
      {res.status === 'unavailable' ? (
        <ModeState
          title="REQUIRES THE LIVE GATE API"
          reason="Set VITE_API_BASE_URL and start the API. This page has no captured fixture on purpose: a counterfactual computed from placeholder numbers would be a fabricated spec."
          hatch
        />
      ) : null}
      {res.status === 'error' ? <ModeState title="COULD NOT LOAD THIS RUN" reason={res.message} hatch /> : null}

      {data ? (
        <>
          <div className="syn-section-head" style={{ margin: '28px 0 14px' }}>
            <span className="syn-section-marker">A</span>
            <span className="syn-section-kicker">THE MINIMUM CHANGE</span>
            <span className="syn-section-rule" />
          </div>
          <Plan data={data} />

          {data.stability.map((s) => (
            <div className="an-section" key={`s-${s.target}`}>
              <div className="syn-section-head" style={{ margin: '0 0 14px' }}>
                <span className="syn-section-marker">B</span>
                <span className="syn-section-kicker">STABILITY LENS — {s.target}</span>
                <span className="syn-section-rule" />
              </div>
              <div style={{ marginBottom: 14 }}>
                <AxisLabel axis="N" size="sm" title="STABILITY / CONCURRENCY" sub={null} />
              </div>
              <StabilityBlock s={s} key={`${data.commit}-${s.target}`} />
            </div>
          ))}

          {data.complexity.map((c) => (
            <div className="an-section" key={`c-${c.target}`}>
              <div className="syn-section-head" style={{ margin: '0 0 14px' }}>
                <span className="syn-section-marker">C</span>
                <span className="syn-section-kicker">COMPLEXITY LENS — {c.target}</span>
                <span className="syn-section-rule" />
              </div>
              <div style={{ marginBottom: 14 }}>
                <AxisLabel axis="n" size="sm" title="COMPLEXITY / INPUT SIZE" sub={null} />
              </div>
              <ComplexityBlock c={c} ceilingS={ceilingS} onCeiling={setCeilingS} key={`${data.commit}-${c.target}`} />
            </div>
          ))}
        </>
      ) : null}

      <div className="an-notes">
        <div className="an-note">
          <div className="an-note-label">HOW THESE NUMBERS ARE MADE</div>
          <div className="an-note-body">
            <ul>
              <li>Equilibria are the exact roots of load = N / R(N) for the fitted USL, snapped to the gate’s own integer grid so a quoted headroom is the one the gate computes.</li>
              <li>Every threshold is found by bisection on the gate’s decision rule, and tests/check_18 verifies each lever flips the real gate at the quoted value — and not 2% past it.</li>
              <li>κ levers hold base latency and σ at their fitted values; load levers hold the whole fitted curve.</li>
              <li>Ceiling crossings extrapolate from the largest measured n and move if the named ceiling moves.</li>
              <li>A lens that could not decide gets no counterfactual: there is no law to vary.</li>
            </ul>
          </div>
        </div>
        <div className="an-note an-note--roadmap">
          <div className="an-note-label">NOT BUILT — THE ORIGINAL CONCEPT</div>
          <div className="an-note-body">
            The first design for this page was a per-line impact wave propagating across the dependency
            graph, weighted by a differentiable twin’s gradient. That remains a roadmap concept: it needs a
            model fitted across the whole graph. Everything above is computed from laws measured on the
            declared targets — nothing on this page is a placeholder.
          </div>
        </div>
      </div>
    </div>
  );
}
