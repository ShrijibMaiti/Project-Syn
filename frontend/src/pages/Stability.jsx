import { useEffect, useState } from 'react';

import { getStability } from '../api/endpoints.js';
import { STABILITY } from '../api/fixtures.js';
import AxisLabel from '../components/AxisLabel.jsx';
import StatCard from '../components/StatCard.jsx';
import {
  MeasuringPanel,
  ProbeFailurePanel,
  ProbeModeSwitch,
} from '../components/ProbeStates.jsx';
import CapacityCurve from '../charts/CapacityCurve.jsx';
import LatencyCurve from '../charts/LatencyCurve.jsx';

const MEASURING_LOG = [
  '> load_driver: sweeping N = 1 … 256',
  '> level 9/14 (N = 48) ........ 22s / 30s',
  '> samples collected: 84,312',
];

const FAILURE_LOG = `> stability.capacity_probe start
> connecting checkout-api:8443 ......... [OK]
> warmup N=1 .......................... [OK]
> sweep N=2 ........................... [ERR]
>   ConnectionResetError: peer closed
>   at telemetry/load_driver.py:118
> retry 1/3 ........................... [ERR]
> retry 2/3 ........................... [ERR]
> retry 3/3 ........................... [ERR]
> ABORT after 41.2s — 0 usable levels
> verdict contribution: NONE (not a pass)`;

const RISING_ONLY = `      ___----
   __-
 _-
/`;

const RISE_THEN_FALL = `   _--_
 _-    -_
/        --___`;

export default function Stability({ mode, onModeChange }) {
  const [data, setData] = useState(STABILITY);

  useEffect(() => {
    let live = true;
    getStability().then((payload) => {
      if (live) setData(payload);
    });
    return () => {
      live = false;
    };
  }, []);

  // A decline only exists if the curve is humped. On a monotone curve,
  // "1x decline" would describe a collapse that never happened.
  const lastThr = data.points[data.points.length - 1][2];
  const humped = data.humped ?? (lastThr < data.peak.throughput * 0.95);
  const declineFactor = Math.round(data.peak.throughput / lastThr);
  const hasTrap = data.separatrix !== null && data.separatrix !== undefined;
  // Spread bars scale to this run's worst level, never below 10%.
  const spreadScale = Math.max(10, ...data.points.map((p) => p[3] ?? 0));

  return (
    <div className="syn-page">
      <div className="syn-page-head">
        <div>
          <AxisLabel axis="N" size="md" sub="SIMULTANEOUS REQUESTS — NOT INPUT SIZE" />
          <h1 className="syn-page-title">Capacity curve</h1>
          <div className="syn-page-meta">
            {data.target} · {data.levels} concurrency levels · N = 1 → {data.nMax ?? data.points[data.points.length - 1][0]}
          </div>
        </div>
        <ProbeModeSwitch mode={mode} onChange={onModeChange} />
      </div>

      {mode === 'ok' && (
        <div>
          <div className="syn-panel">
            <div className="syn-panel-head">
              <span className="syn-panel-title">THROUGHPUT × N</span>
              <span className="syn-panel-meta">
                {humped
                  ? `RISE · PEAK · COLLAPSE — ${declineFactor}× DECLINE`
                  : 'MONOTONE — NO PEAK, NO TRAP POSSIBLE'}
              </span>
            </div>
            <div className="syn-chart-body">
              <CapacityCurve data={data} />
            </div>
            <div className="syn-legend">
              <span className="syn-legend-item">
                <span className="syn-swatch-line" />
                MEASURED THROUGHPUT
              </span>
              {hasTrap && (
                <>
                  <span className="syn-legend-item">
                    <span className="syn-swatch-dashed" />
                    SEPARATRIX
                  </span>
                  <span className="syn-legend-item">
                    <span className="syn-swatch-hatch" />
                    TRAPPED REGION — NO SELF-RECOVERY
                  </span>
                </>
              )}
            </div>
          </div>

          <div className="syn-stat-strip">
            {data.stats.map((stat) => (
              <StatCard key={stat.label} size="sm" {...stat} />
            ))}
          </div>

          <div className="syn-panel" style={{ marginTop: 24 }}>
            <div className="syn-panel-head">
              <span className="syn-panel-title">LATENCY × N — TWO FITTED MODELS</span>
              <span className="syn-panel-meta">LOG LATENCY / ms</span>
            </div>
            <div className="syn-chart-body">
              <LatencyCurve data={data} />
            </div>
            <div className="syn-legend">
              <span className="syn-legend-item">
                <span className="syn-swatch-square" />
                MEASURED
              </span>
              <span className="syn-legend-item">
                <span className="syn-swatch-line" />
                MODEL B — WITH COHERENCY COST κ
              </span>
              <span className="syn-legend-item">
                <span className="syn-swatch-dashed-grey" />
                MODEL A — κ = 0
              </span>
            </div>
          </div>

          <div className="syn-section-head" style={{ margin: '32px 0 14px' }}>
            <span className="syn-section-marker">□</span>
            <span className="syn-section-kicker">MEASURED POINTS</span>
            <span className="syn-section-rule" />
          </div>
          <div className="syn-table syn-table--scroll">
            <div className="stability-table-inner">
              <div className="syn-table-head stability-head-row">
                <div>N</div>
                <div className="syn-align-right">LATENCY ms</div>
                <div className="syn-align-right">THROUGHPUT rps</div>
                <div title="(max ÷ min − 1) across repeated rounds at this level">REPEAT SPREAD %</div>
              </div>
              {data.points.map(([n, latency, throughput, cv]) => {
                // A peak is only a peak on a humped curve; on a monotone curve the
                // highest point is just the last one. Guard the separatrix: in JS
                // `n > null` is `n > 0`, which would mark every row trapped.
                const isPeak = humped && n === data.peak.n;
                const isTrapped = hasTrap && n > data.separatrix;
                return (
                  <div
                    key={n}
                    className={`stability-row${isPeak ? ' stability-row--peak' : ''}${
                      isTrapped ? ' stability-row--trapped' : ''
                    }`}
                  >
                    <div className="stability-cell">{n}</div>
                    <div className="stability-cell stability-cell--lat">
                      {latency.toLocaleString('en-US')}
                    </div>
                    <div className="stability-cell stability-cell--thr">{throughput.toFixed(1)}</div>
                    <div className="stability-cell stability-cell--cv">
                      <span className="stability-cv-track">
                        <span
                          className="syn-meter-fill"
                          style={{ width: `${Math.min(100, (cv / spreadScale) * 100).toFixed(0)}%` }}
                        />
                      </span>
                      <span className="stability-cv-label">{cv.toFixed(1)}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="stability-shapes">
            <div className={`stability-shape${humped ? '' : ' stability-shape--lit'}`}>
              <div className="stability-shape-label">
                IF THE CURVE ONLY RISES{humped ? '' : ' — THIS SERVICE'}
              </div>
              <pre className="syn-ascii stability-shape-art">{RISING_ONLY}</pre>
              <div className="stability-shape-body">
                No trap is possible. Throughput saturates but the system stays on the healthy branch;
                adding load costs latency, never recovery.
              </div>
            </div>
            <div className={`stability-shape${humped ? ' stability-shape--lit' : ''}`}>
              <div className="stability-shape-label">
                IF IT RISES THEN FALLS{humped ? ' — THIS SERVICE' : ''}
              </div>
              <pre className="syn-ascii stability-shape-art">{RISE_THEN_FALL}</pre>
              <div className="stability-shape-body">
                {hasTrap
                  ? `A cliff exists, and SYN can locate it. Past N = ${Number(data.separatrix).toFixed(1)} the service enters a second stable state and does not climb out when load is removed. Only a manual reset recovers it.`
                  : humped
                    ? 'A peak exists, so a cliff exists in principle — but no separatrix falls within the assumed operating load.'
                    : 'A cliff exists, and SYN can locate it: past the separatrix the service enters a second stable state and does not climb out when load is removed.'}
              </div>
            </div>
          </div>
        </div>
      )}

      {mode !== 'ok' && (
        <div className="syn-page-meta" style={{ margin: '0 0 12px' }}>
          STATE PREVIEW — ILLUSTRATIVE ONLY, NOT THIS RUN&apos;S DATA
        </div>
      )}

      {mode === 'loading' && (
        <MeasuringPanel
          label="MEASUREMENT IN PROGRESS — DO NOT INTERRUPT"
          lines={MEASURING_LOG}
          percent={61}
          foot="61% · EST. 3m 24s REMAINING"
        />
      )}

      {mode === 'insufficient' && (
        <div className="syn-insufficient">
          <div className="syn-insufficient-head">
            <div className="syn-insufficient-kicker">VERDICT INPUT</div>
            <div className="syn-insufficient-title">
              <span>[?]</span>
              <span>INSUFFICIENT EVIDENCE</span>
            </div>
            <div className="syn-insufficient-body">
              SYN ran and could not gather enough data to decide. <b>This is not a pass.</b> Only 3
              concurrency levels completed before the probe window closed (minimum 16), and the sweep
              never reached N = 256, so κ cannot be distinguished from zero and no separatrix can be
              located.
            </div>
          </div>
          <div className="syn-insufficient-metrics">
            <div>
              <div className="syn-insufficient-metric-label">LEVELS SAMPLED</div>
              <div className="syn-insufficient-metric-value">3 / 16 required</div>
            </div>
            <div>
              <div className="syn-insufficient-metric-label">MAX N REACHED</div>
              <div className="syn-insufficient-metric-value">16 / 256 required</div>
            </div>
            <div>
              <div className="syn-insufficient-metric-label">PEAK OBSERVED</div>
              <div className="syn-insufficient-metric-value">NO</div>
            </div>
          </div>
        </div>
      )}

      {mode === 'failed' && (
        <ProbeFailurePanel
          log={FAILURE_LOG}
          foot="The stability lens contributed nothing to this verdict. A certificate assembled without it is marked UNKNOWN, never PASS."
        />
      )}
    </div>
  );
}
