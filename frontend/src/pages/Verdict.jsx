import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { getRuns, getVerdict, toState } from '../api/endpoints.js';
import { RUN, VERDICTS, VERDICT_STATES } from '../api/fixtures.js';
import VerdictBadge, { RiskChip } from '../components/VerdictBadge.jsx';
import AxisLabel from '../components/AxisLabel.jsx';
import ProbeTimings from '../components/ProbeTimings.jsx';
import { ROUTES } from '../App.jsx';

const COPY_RESET_MS = 1600;

/** Most severe first, so the switcher reads as a scale. */
const RUN_ORDER = { REFUSED: 0, WARN: 1, UNKNOWN: 2, PASS: 3 };

export default function Verdict() {
  const navigate = useNavigate();
  const { search } = useLocation();
  // Keep the selected run (?run=) when jumping to a lens page.
  const go = (pathname) => navigate({ pathname, search });
  const [state, setState] = useState('REFUSED');
  const [cert, setCert] = useState(VERDICTS.REFUSED);
  const [copied, setCopied] = useState(false);
  const [runs, setRuns] = useState([]);

  // Every stored run, so each verdict state can be shown from a REAL
  // measurement rather than a simulated certificate.
  useEffect(() => {
    let on = true;
    getRuns().then((r) => {
      if (on) setRuns(r?.runs ?? []);
    });
    return () => {
      on = false;
    };
  }, []);

  useEffect(() => {
    let live = true;
    getVerdict(state).then((payload) => {
      if (live) setCert(payload);
    });
    return () => {
      live = false;
    };
  }, [state, search]);

  useEffect(() => {
    if (!copied) return undefined;
    const timer = setTimeout(() => setCopied(false), COPY_RESET_MS);
    return () => clearTimeout(timer);
  }, [copied]);

  const copyCertificate = async () => {
    try {
      await navigator.clipboard.writeText(cert.certificateText);
      setCopied(true);
    } catch {
      // clipboard unavailable (insecure context, denied permission) — the
      // download path below still gets the operator their certificate
    }
  };

  const downloadCertificate = () => {
    const blob = new Blob([cert.certificateText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `syn-certificate-${cert.commit ?? RUN.commitShort}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="syn-page">
      <div className="syn-switch-row syn-switch-row--verdict">
        {cert.live ? (
          <>
            {/* Each button is a stored, measured run. Switching shows a different
                measurement -- never overrides one. */}
            <span className="syn-switch-label">STORED RUNS — EVERY VERDICT MEASURED</span>
            {[...runs]
              .sort((a, b) => RUN_ORDER[toState(a.risk)] - RUN_ORDER[toState(b.risk)])
              .map((r) => {
                const active = r.commit === cert.commit;
                return (
                  <button
                    key={r.commit}
                    type="button"
                    className={`syn-switch${active ? ' active' : ''}`}
                    aria-pressed={active}
                    onClick={() => {
                      setCopied(false);
                      navigate({ pathname: ROUTES.verdict, search: `?run=${encodeURIComponent(r.commit)}` });
                    }}
                  >
                    {toState(r.risk)} · {r.commit}
                  </button>
                );
              })}
          </>
        ) : (
          <>
            <span className="syn-switch-label">SIMULATE VERDICT — CAPTURED FIXTURE</span>
            {VERDICT_STATES.map((option) => (
              <button
                key={option}
                type="button"
                className={`syn-switch${state === option ? ' active' : ''}`}
                aria-pressed={state === option}
                onClick={() => {
                  setState(option);
                  setCopied(false);
                }}
              >
                {option}
              </button>
            ))}
          </>
        )}
      </div>

      <div className="verdict-cert">
        <VerdictBadge state={cert.state} glyph={cert.glyph} summary={cert.summary} />

        <div className="verdict-meta">
          {cert.certificate.map((row) => (
            <div className="verdict-meta-row" key={row.k}>
              <span className="verdict-meta-k">{row.k}</span>
              <span className="verdict-meta-v">{row.v}</span>
            </div>
          ))}
          <div className="verdict-actions">
            <button type="button" className="verdict-action" onClick={copyCertificate}>
              {copied ? 'COPIED ✓' : 'COPY CERTIFICATE'}
            </button>
            <button type="button" className="verdict-action" onClick={downloadCertificate}>
              DOWNLOAD .TXT
            </button>
          </div>
        </div>
      </div>

      <div className="syn-section-head">
        <span className="syn-section-marker">A</span>
        <span className="syn-section-kicker">FINDINGS — PROBES THAT RAN</span>
        <span className="syn-section-rule" />
      </div>
      <div className="syn-panel">
        <div className="syn-table-head verdict-findings-head">
          <div>PROBE</div>
          <div>FINDING</div>
          <div className="syn-align-right">RISK</div>
        </div>
        {cert.findings.map((finding, i) => (
          <div className="syn-table-row verdict-findings-row" key={`${finding.probe}-${i}`}>
            <div className="verdict-findings-probe">{finding.probe}</div>
            <div className="verdict-findings-text">{finding.finding}</div>
            <div className="verdict-findings-risk">
              <RiskChip risk={finding.risk} />
            </div>
          </div>
        ))}
      </div>

      <div className="verdict-lenses">
        <div className="syn-panel">
          <div className="verdict-lens-head">
            <AxisLabel axis="n" size="sm" title="COMPLEXITY / INPUT SIZE" sub={null} />
          </div>
          <div className="verdict-lens-body">
            <div className="verdict-lens-target-label">TARGET</div>
            <div className="verdict-lens-target">{cert.complexity.target}</div>
            <div className="verdict-exp-row">
              <div>
                <div className="verdict-exp-label">GROWTH EXPONENT</div>
                <div className="verdict-exp-value">{cert.complexity.exponent}</div>
              </div>
              <div className="verdict-exp-ci">{cert.complexity.ci}</div>
            </div>
            <div
              className={`verdict-superlinear verdict-superlinear--${
                cert.complexity.superlinear ? 'on' : 'off'
              }`}
            >
              {cert.complexity.superlinearLabel}
            </div>
            <button
              type="button"
              className="verdict-lens-link"
              onClick={() => go(ROUTES.complexity)}
            >
              OPEN SCALING LAW -&gt;
            </button>
          </div>
        </div>

        <div className="syn-panel">
          <div className="verdict-lens-head">
            <AxisLabel axis="N" size="sm" title="STABILITY / CONCURRENCY" sub={null} />
          </div>
          <div className="verdict-lens-body">
            <div className="verdict-lens-target-label">TARGET</div>
            <div className="verdict-lens-target verdict-lens-target--tight">
              {cert.stabilityTarget ?? RUN.stabilityTarget}
            </div>
            {cert.stability.map((row) => (
              <div className="syn-kv" key={row.k}>
                <span className="syn-kv-k">{row.k}</span>
                <span className="syn-kv-v">{row.v}</span>
              </div>
            ))}
            <button
              type="button"
              className="verdict-lens-link verdict-lens-link--plain"
              onClick={() => go(ROUTES.stability)}
            >
              OPEN CAPACITY CURVE -&gt;
            </button>
          </div>
        </div>
      </div>

      {cert.remediation.length > 0 && (
        <div>
          <div className="syn-section-head">
            <span className="syn-section-marker">B</span>
            <span className="syn-section-kicker">REMEDIATION — WHAT WOULD LIFT THE REFUSAL</span>
            <span className="syn-section-rule" />
          </div>
          <div className="syn-panel--lit">
            {cert.remediation.map((step) => (
              <div className="verdict-remediation-row" key={step.num}>
                <div className="verdict-remediation-num">{step.num}</div>
                <div className="verdict-remediation-body">
                  <div className="verdict-remediation-title">{step.title}</div>
                  <div className="verdict-remediation-copy">{step.body}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="syn-section-head">
        <span className="syn-section-marker">{cert.remediation.length > 0 ? 'C' : 'B'}</span>
        <span className="syn-section-kicker">PROBE TIMINGS</span>
        <span className="syn-section-rule" />
      </div>
      <ProbeTimings timings={cert.timings} total={cert.totalWallClock} />

      <div className="verdict-disclaimer">
        These are statistical early warnings with stated p-values, not proofs. Every exponent,
        coherency cost and crossing on this certificate is an estimate from measured telemetry,
        carrying the confidence interval printed beside it. A ceiling crossing moves when the named
        ceiling moves. SYN refuses with grounds; it does not claim certainty.
      </div>
    </div>
  );
}
