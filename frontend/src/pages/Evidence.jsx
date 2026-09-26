import { useEffect, useState } from 'react';

import { getEvidence } from '../api/endpoints.js';
import { EVIDENCE } from '../api/fixtures.js';
import EvidenceRow, { ParameterRow } from '../components/EvidenceRow.jsx';

/**
 * The statistics behind the stability verdict.
 *
 * Every sentence that asserts an OUTCOME (which model won, whether a trap
 * exists, where the separatrix sits) is derived from the run. What stays
 * written in is METHOD: what the two models are, why R² is not the criterion,
 * and the thresholds each verdict is held to.
 */
export default function Evidence() {
  const [data, setData] = useState(EVIDENCE);

  useEffect(() => {
    let live = true;
    getEvidence().then((payload) => {
      if (live) setData(payload);
    });
    return () => {
      live = false;
    };
  }, []);

  // Emphasis follows the verdict: the selected model is lit, the rejected dim.
  const modelClass = (m) =>
    `evidence-model evidence-model--${m.verdict === 'SELECTED' ? 'selected' : 'rejected'}`;
  const modelChip = (m) =>
    m.verdict === 'SELECTED' ? 'evidence-adequacy-chip' : 'syn-chip syn-chip--outline';

  const levels = data.levels ?? 14;
  const nMax = data.nMax ?? 256;
  const gof = data.goodnessOfFit ?? {};

  return (
    <div className="syn-page">
      <div className="phase2-header">
        <div className="syn-page-kicker">STATISTICAL EVIDENCE BEHIND THE STABILITY VERDICT</div>
        <h1 className="syn-page-title">Model comparison</h1>
        <p className="syn-page-lead">
          Two competing models fitted to the same {levels} measured concurrency levels, N = 1 →{' '}
          {nMax}. The question is not whether either model looks good — it is whether adding a
          coherency cost term explains the data better than chance.
        </p>
      </div>

      <div className="evidence-models">
        {[data.modelA, data.modelB].map((m) => (
          <div className={modelClass(m)} key={m.label}>
            <div className="evidence-model-head">
              <span className="evidence-model-label">{m.label}</span>
              <span className={modelChip(m)}>{m.verdict}</span>
            </div>
            <pre className="evidence-model-formula">{m.formula}</pre>
            {m.rows.map((row) => (
              <EvidenceRow
                key={row.k}
                label={row.k}
                value={row.v}
                selected={m.verdict === 'SELECTED'}
              />
            ))}
            <div className="evidence-model-foot">{m.foot}</div>
          </div>
        ))}
      </div>

      <div className="evidence-tests">
        {data.tests.map((test) => (
          <div key={test.label}>
            <div className="evidence-test-label">{test.label}</div>
            <div className="evidence-test-value">{test.value}</div>
            <div className="evidence-test-note">{test.note}</div>
          </div>
        ))}
      </div>

      <div className="syn-section-head" style={{ margin: '34px 0 14px' }}>
        <span className="syn-section-marker">≡</span>
        <span className="syn-section-kicker">PARAMETER ESTIMATES</span>
        <span className="syn-section-rule" />
      </div>
      <div className="syn-panel">
        <div className="syn-table-head evidence-params-head">
          <div>PARAMETER</div>
          <div className="syn-align-right">ESTIMATE</div>
          <div className="syn-align-right">95% CI</div>
          <div className="syn-align-right">p</div>
        </div>
        {data.parameters.map((param) => (
          <ParameterRow key={param.name} {...param} />
        ))}
      </div>

      <div className="evidence-lower">
        <div className="syn-panel">
          <div className="evidence-adequacy-head">
            <span className="evidence-adequacy-label">MEASUREMENT ADEQUACY</span>
            <span
              className={
                data.adequate === false ? 'syn-chip syn-chip--outline' : 'evidence-adequacy-chip'
              }
            >
              {data.adequate === false ? 'INSUFFICIENT' : 'PASS'}
            </span>
          </div>
          <div className="evidence-adequacy-body">
            {data.adequacy.map((item) => (
              <div className="evidence-adequacy-item" key={item.k}>
                <div className="evidence-adequacy-row">
                  <span className="evidence-adequacy-k">{item.k}</span>
                  <span>{item.v}</span>
                </div>
                {Number.isFinite(item.fillPct) ? (
                  <>
                    <div className="evidence-adequacy-meter">
                      <div
                        className="evidence-adequacy-fill"
                        style={{ width: `${item.fillPct}%` }}
                      />
                      <div
                        className="evidence-adequacy-req-marker"
                        style={{ left: `${item.reqPct}%` }}
                      />
                    </div>
                    <div className="evidence-adequacy-req">{item.req}</div>
                  </>
                ) : null}
              </div>
            ))}
          </div>
        </div>

        <div className="evidence-r2">
          <div className="evidence-r2-label">WHY R² IS NOT THE CRITERION HERE</div>
          <div className="evidence-r2-stats">
            <div>
              <div className="evidence-r2-stat-label">FIT R² — THIS RUN</div>
              <div className="evidence-r2-stat-value">{gof.modelAR2 ?? '—'}</div>
            </div>
            <div>
              <div className="evidence-r2-stat-label">USED FOR THE VERDICT</div>
              <div className="evidence-r2-stat-value">{gof.usedForVerdict ?? 'NO'}</div>
            </div>
          </div>
          <div className="evidence-r2-body">
                        R² measures how much variance a curve explains, not whether the κ estimate is right —
            and it fails in both directions. When latency spans orders of magnitude, relative-error
            weighting drives R² toward 1.0000 almost regardless of κ; in validation it read 0.99
            alongside a 100% error in κ. When latency is flat, there is almost no variance to
            explain and R² falls toward 0 even for a near-perfect fit. SYN therefore decides on the
            nested F-test p-value, never on R².
            {gof.runLine ? (
              <>
                <br />
                <br />
                {gof.runLine}
              </>
            ) : null}
          </div>
        </div>
      </div>

      {data.conclusion ? (
        <div className="evidence-conclusion">
          <div className="evidence-conclusion-label">PLAIN-LANGUAGE CONCLUSION</div>
          <div className="evidence-conclusion-row">
            <span className="evidence-conclusion-badge">{data.conclusion.badge}</span>
            <div className="evidence-conclusion-text">{data.conclusion.text}</div>
          </div>
          <div className="evidence-alternatives">
            {(data.alternatives ?? []).map((alt, i) => (
              <span
                key={alt}
                className={`evidence-alternative${i % 2 ? ' evidence-alternative--dashed' : ''}`}
              >
                ALTERNATIVE: {alt}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <div className="evidence-conclusion">
          <div className="evidence-conclusion-label">PLAIN-LANGUAGE CONCLUSION</div>
          <div className="evidence-conclusion-row">
            <span className="evidence-conclusion-badge">CAPTURED FIXTURE</span>
            <div className="evidence-conclusion-text">
              No live run is loaded. Start the gate API to see the conclusion for a measured run.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
