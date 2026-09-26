import { useEffect, useState } from 'react';

import { getComplexity } from '../api/endpoints.js';
import { COMPLEXITY } from '../api/fixtures.js';
import AxisLabel from '../components/AxisLabel.jsx';
import StatCard from '../components/StatCard.jsx';
import {
  MeasuringPanel,
  ProbeFailurePanel,
  ProbeModeSwitch,
} from '../components/ProbeStates.jsx';
import ScalingLawChart from '../charts/ScalingLawChart.jsx';

/** Exponents are estimates — show two decimals, never raw float noise. */
const fmtExp = (v) => (Number.isFinite(Number(v)) ? Number(v).toFixed(2) : '—');

const MEASURING_LOG = [
  '> multiscale_sweep: n = 32 … 8192',
  '> scale 7/9 (n = 2048) ........ 1204 ms',
  '> symbolic_regressor: queued',
];

const FAILURE_LOG = `> complexity.multiscale_sweep start
> fixture seed n=32 .................. [OK]
> fixture seed n=8192 ................ [ERR]
>   FixtureError: dataset generator OOM
>   at telemetry/multiscale_sweep.py:64
> ABORT — 2 usable scales (need 5)
> verdict contribution: NONE (not a pass)`;

const CANDIDATE_LAWS = ['n log n', 'n^1.5', 'n²', '2.1n + 4000'];

export default function Complexity({ mode, onModeChange }) {
  const [data, setData] = useState(COMPLEXITY);

  useEffect(() => {
    let live = true;
    getComplexity().then((payload) => {
      if (live) setData(payload);
    });
    return () => {
      live = false;
    };
  }, []);

  // The deciding fact is DERIVED from the measurement, never written in.
  // Gate threshold: exponent > 1.2 is superlinear.
  const exp = Number(data.law.exponent);
  const lo = Number(data.law.exponentLow);
  const hi = Number(data.law.exponentHigh);
  const superlinear = data.superlinear ?? exp > 1.2;
  const verdictFact = superlinear
    ? {
        superlinear: true,
        title: 'SUPERLINEAR',
        body:
          lo > 1
            ? `The recovered exponent ${fmtExp(exp)} sits entirely above 1.0 — the lower bound of its interval is ${fmtExp(lo)}. Cost grows faster than input. This alone refuses the merge.`
            : `The recovered exponent ${fmtExp(exp)} exceeds the 1.2 gate threshold, though its interval (${fmtExp(lo)}–${fmtExp(hi)}) reaches down to ${fmtExp(lo)}. Cost grows faster than input.`,
      }
    : {
        superlinear: false,
        title: 'NOT SUPERLINEAR',
        body: `The recovered exponent ${fmtExp(exp)} is below the 1.2 gate threshold${
          hi < 1.2 ? `, and so is the top of its interval (${fmtExp(hi)})` : ''
        }. Cost grows no faster than input. This lens does not object to the merge.`,
      };

  return (
    <div className="syn-page">
      <div className="syn-page-head">
        <div>
          <AxisLabel axis="n" size="md" sub="RECORDS PROCESSED — NOT CONCURRENCY" />
          <h1 className="syn-page-title">Scaling law</h1>
          <div className="syn-page-meta" style={{ wordBreak: 'break-all' }}>
            {data.target} · {data.scales} scales · log-log
          </div>
        </div>
        <ProbeModeSwitch mode={mode} onChange={onModeChange} />
      </div>

      {mode === 'ok' && (
        <div>
          <div className="syn-panel">
            <div className="syn-panel-head">
              <span className="syn-panel-title">RESOURCE COST × n</span>
              <span className="syn-panel-meta">{data.law.display}</span>
            </div>
            <div className="syn-chart-body">
              <ScalingLawChart data={data} />
            </div>
            <div className="syn-legend">
              <span className="syn-legend-item">
                <span className="syn-swatch-square-outline" />
                MEASURED
              </span>
              <span className="syn-legend-item">
                <span className="syn-swatch-line" />
                FITTED LAW
              </span>
              <span className="syn-legend-item">
                <span className="syn-swatch-dashed-thin" />
                95% EXPONENT BAND
              </span>
              <span className="syn-legend-item">
                <span className="syn-swatch-range" />
                SAMPLED RANGE
              </span>
            </div>
          </div>

          <div className="syn-stat-strip syn-stat-strip--wide">
            {data.stats.map((stat) => (
              <StatCard key={stat.label} size="sm" {...stat} />
            ))}
          </div>

          <div className="complexity-facts">
            <div className={verdictFact.superlinear ? 'complexity-fact--inverted' : 'complexity-fact'}>
              <div className="complexity-fact-kicker">THE FACT THAT DECIDES THE VERDICT</div>
              <div className="complexity-fact-value">{verdictFact.title}</div>
              <div className="complexity-fact-body">{verdictFact.body}</div>
            </div>
            <div className="complexity-law">
              <div className="complexity-law-kicker">FITTED LAW — TAIL EXPONENT</div>
              <pre className="complexity-law-formula">{data.law.display}</pre>
              <div className="complexity-law-body">
                Measured exponent {fmtExp(data.law.exponent)} (95% CI {fmtExp(data.law.exponentLow)}
                –{fmtExp(data.law.exponentHigh)}) · {data.scales} scales from n ={' '}
                {data.points[0][0].toLocaleString('en-US')} to n ={' '}
                {data.points[data.points.length - 1][0].toLocaleString('en-US')}.
                <br />
                {verdictFact.superlinear
                  ? 'The ceiling crossing is an extrapolation: it moves if the named ceiling moves.'
                  : 'No ceiling crossing is predicted: extrapolating non-superlinear growth to a ceiling would produce a meaningless number.'}
              </div>
            </div>
          </div>
        </div>
      )}

      {mode === 'loading' && (
        <MeasuringPanel
          label="MULTISCALE SWEEP RUNNING"
          lines={MEASURING_LOG}
          percent={74}
          foot="74% · EST. 1m 06s REMAINING"
        />
      )}

      {mode === 'insufficient' && (
        <div className="syn-insufficient">
          <div className="syn-insufficient-head">
            <div className="syn-insufficient-kicker">SCALE-SPREAD GUARD — TRIPPED</div>
            <div className="syn-insufficient-title">
              <span>[?]</span>
              <span>RANGE TOO NARROW</span>
            </div>
            <div className="syn-insufficient-body syn-insufficient-body--wide">
              Telemetry spans <b>0.6 orders of magnitude</b> (n = 512 to n = 2048). Below the 2.0
              minimum, n·log n, n^1.5 and n² are statistically indistinguishable — every one of them
              fits these points. SYN reports insufficient evidence rather than a fabricated law.{' '}
              <b>This is not a pass.</b>
            </div>
          </div>
          <div className="complexity-candidates">
            <div className="complexity-candidates-label">CANDIDATE LAWS THAT FIT EQUALLY WELL</div>
            <div className="complexity-candidates-row">
              {CANDIDATE_LAWS.map((law) => (
                <span className="complexity-candidate" key={law}>
                  {law}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {mode === 'failed' && (
        <ProbeFailurePanel
          log={FAILURE_LOG}
          foot="No law was fitted. The complexity lens is absent from this certificate, which caps the verdict at UNKNOWN."
        />
      )}
    </div>
  );
}
