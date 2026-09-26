import { useEffect, useState } from 'react';

import { formatTimestamp, getBlindDetection } from '../api/endpoints.js';
import { BLIND_DETECTION } from '../api/fixtures.js';
import StatCard from '../components/StatCard.jsx';
import ConfusionMatrix from '../charts/ConfusionMatrix.jsx';

export default function BlindDetection() {
  const [data, setData] = useState(BLIND_DETECTION);

  useEffect(() => {
    let live = true;
    getBlindDetection().then((payload) => {
      if (live) setData(payload);
    });
    return () => {
      live = false;
    };
  }, []);

  return (
    <div className="syn-page">
      <div className="phase2-header">
        <div className="syn-page-kicker">INTEGRITY PROOF — DETECTION WITHOUT LABELS</div>
        <h1 className="syn-page-title">Blind detection</h1>
        <p className="syn-page-lead syn-page-lead--wide">
          SYN is handed anonymised, shuffled candidate targets with every label stripped. It must
          decide which are risky using measurement alone. Scoring happens afterwards, outside the
          system, against a ground-truth file SYN never reads.
        </p>
        {data.recordedAt ? (
          <div className="syn-page-meta">
            stored result · recorded {formatTimestamp(data.recordedAt)} · {data.seeds.length}{' '}
            seeds · independent of the selected run
          </div>
        ) : null}
      </div>

      <div className="blind-upper">
        <ConfusionMatrix
          confusion={data.confusion}
          targetCount={data.targets.length}
          seedLabel={data.shownSeed ?? 0}
        />

        <div className="blind-stats">
          {data.stats.map((stat) => (
            <StatCard key={stat.label} size="md" {...stat} />
          ))}
        </div>
      </div>

      <div className="syn-section-head" style={{ margin: '34px 0 14px' }}>
        <span className="syn-section-marker">▤</span>
        <span className="syn-section-kicker">
          PER-TARGET RESULTS — SEED {data.shownSeed ?? 0}
        </span>
        <span className="syn-section-rule" />
      </div>
      <div className="syn-table syn-table--scroll">
        <div className="blind-table-inner">
          <div className="syn-table-head blind-head-row">
            <div>TARGET</div>
            <div>SYN SAID</div>
            <div>WHAT IT ACTUALLY WAS</div>
            <div>CORRECT</div>
            <div className="syn-align-right">MEASURED VALUE</div>
          </div>
          {data.targets.map((target) => (
            <div
              className={`blind-row${target.trap ? ' blind-row--trap' : ''}${
                target.correct === false ? ' blind-row--wrong' : ''
              }`}
              key={target.id}
            >
              <div className="blind-cell">{target.id}</div>
              <div className="blind-cell">
                <span
                  className={`syn-chip ${
                    target.decision === 'REFUSE' ? 'syn-chip--solid' : 'syn-chip--outline'
                  }`}
                >
                  {target.decision}
                </span>
              </div>
              <div className="blind-cell blind-cell--truth">
                {target.truth}
                {target.trap ? <span className="blind-trap-tag">TRAP</span> : null}
              </div>
              <div
                className={`blind-cell${target.correct === false ? ' blind-cell--wrong' : ''}`}
                title={target.outcome || undefined}
              >
                {target.correct === true
                  ? '✓'
                  : target.correct === false
                    ? `✗ ${target.outcome === 'FP' ? 'FALSE POS' : 'MISSED'}`
                    : target.correct === null
                      ? '— ABSTAINED'
                      : '✓'}
              </div>
              <div className="blind-cell blind-cell--measure">{target.measure}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="blind-lower">
        <div className="syn-panel">
          <div className="blind-panel-head">STABILITY ACROSS SEEDS</div>
          <div className="blind-seeds-body">
            {data.seeds.map((seed) => (
              <div className="blind-seed-row" key={seed.name}>
                <span className="blind-seed-name">{seed.name}</span>
                <span className="blind-seed-metric">TP {seed.tp}</span>
                <span className="blind-seed-metric">FP {seed.fp}</span>
                <span className="blind-seed-rate">{seed.rate}</span>
              </div>
            ))}
            <div className="blind-seeds-foot">
              {data.seedFoot ??
                'Identical outcome under three independent shuffles — the result is not an artifact of presentation order.'}
            </div>
          </div>
        </div>

        <div className="blind-scope">
          <div className="blind-scope-label">SCOPE OF THIS CLAIM</div>
          <div className="blind-scope-body">
            This validates <b>classification</b>: given a set of candidate targets, SYN picks out the
            risky ones without being told which. It does <b>not</b> validate automatic candidate
            selection across a large repository. Choosing what to probe in a codebase of ten thousand
            functions is a separate, unproven problem.
          </div>
        </div>
      </div>
    </div>
  );
}
