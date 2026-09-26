import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getLanding } from '../api/endpoints.js';
import { LANDING } from '../api/fixtures.js';
import AxisLabel from '../components/AxisLabel.jsx';
import StatCard from '../components/StatCard.jsx';
import { ROUTES } from '../App.jsx';

const WORDMARK = `███████╗██╗   ██╗███╗   ██╗
██╔════╝╚██╗ ██╔╝████╗  ██║
███████╗ ╚████╔╝ ██╔██╗ ██║
╚════██║  ╚██╔╝  ██║╚██╗██║
███████║   ██║   ██║ ╚████║
╚══════╝   ╚═╝   ╚═╝  ╚═══╝`;

const SCHEMATIC = `┌────────────────────────────────────┐
│  MEASURED LAWS — NO FAILURE NEEDED │
│                                    │
│  ┌──────────────┐ ┌──────────────┐ │
│  │ COMPLEXITY   │ │ STABILITY    │ │
│  │ axis: n      │ │ axis: N      │ │
│  │ fitted law   │ │ capacity     │ │
│  │ → ceiling    │ │ → separatrix │ │
│  └──────┬───────┘ └──────┬───────┘ │
│         └────────┬───────┘         │
│            RISK AGGREGATOR         │
└───────────────────┬────────────────┘
                    ▼
       PASS · WARN · REFUSED · UNKNOWN`;

const BOOT_TICK_MS = 480;
const BOOT_HOLD_TICKS = 5;

/** Types the boot log out line by line, holds on the verdict, then loops. */
function useBootLog(lineCount) {
  const [shown, setShown] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setShown((n) => (n >= lineCount + BOOT_HOLD_TICKS ? 0 : n + 1));
    }, BOOT_TICK_MS);
    return () => clearInterval(timer);
  }, [lineCount]);

  return Math.min(shown, lineCount);
}

export default function Landing() {
  const navigate = useNavigate();
  const [data, setData] = useState(LANDING);
  const visibleBootLines = useBootLog(data.bootLines.length);

  useEffect(() => {
    let live = true;
    getLanding().then((payload) => {
      if (live) setData(payload);
    });
    return () => {
      live = false;
    };
  }, []);

  return (
    <div className="landing">
      <section className="landing-hero">
        <div className="landing-inner">
          <div className="landing-kicker">
            MERGE-GATE / EVIDENCE ENGINE / FOR DEVELOPERS AND ENGINEERING LEADS
          </div>

          <div className="landing-banner">
            <div className="landing-banner-sweep" />
            <pre className="syn-ascii landing-banner-art" aria-label="SYN">
              {WORDMARK}
            </pre>
          </div>

          <h1 className="landing-headline">Finds the failure point without triggering the failure.</h1>

          <p className="landing-copy">
            SYN inspects a codebase, measures how it actually behaves, and reads the laws behind
            those measurements to decide whether a change is safe to merge. It does not run the
            system until it breaks. It approves, warns, or refuses — with the evidence attached.
          </p>

          <div className="landing-ctas">
            <button
              type="button"
              className="landing-cta landing-cta--primary"
              onClick={() => navigate(ROUTES.verdict)}
            >
              OPEN THE GATE -&gt;
            </button>
            <button
              type="button"
              className="landing-cta landing-cta--secondary"
              onClick={() => navigate(ROUTES.stability)}
            >
              SEE A CAPACITY CURVE
            </button>
          </div>
        </div>
      </section>

      <section className="landing-ticker" aria-hidden="true">
        <div className="landing-ticker-track">
          <span>{data.ticker}</span>
          <span>{data.ticker}</span>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-inner">
          <div className="landing-section-head">
            <span className="landing-section-num">01</span>
            <span className="landing-section-kicker">VOCABULARY — THE ONE RULE</span>
          </div>
          <h2 className="landing-h2">Two quantities. Never interchangeable.</h2>
          <p className="landing-lead">
            Both are commonly called “scale.” SYN keeps them strictly apart, in every axis, label and
            caption.
          </p>

          <div className="landing-vocab">
            <div className="landing-vocab-cell">
              <AxisLabel axis="n" size="lg" />
              <p className="landing-vocab-copy">
                How a function’s cost grows as it is handed more records. Measured across orders of
                magnitude, then fitted to a closed-form law that can be evaluated at production
                scale.
              </p>
              <div className="landing-vocab-foot">
                OUTLINED GLYPH · LOG-LOG AXES · COMPLEXITY LENS
              </div>
            </div>
            <div className="landing-vocab-cell">
              <AxisLabel axis="N" size="lg" />
              <p className="landing-vocab-copy">
                How a service’s latency grows as more requests run at once. The shape of that curve
                says whether a cliff exists — and if it does, where it is.
              </p>
              <div className="landing-vocab-foot">FILLED GLYPH · LINEAR-N AXES · STABILITY LENS</div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-inner">
          <div className="landing-section-head">
            <span className="landing-section-num">02</span>
            <span className="landing-section-kicker">VERIFIED RESULTS</span>
          </div>
          <h2 className="landing-h2 landing-h2--gap">Measured, not asserted.</h2>

          <div className="landing-stats">
            {data.stats.map((stat) => (
              <StatCard key={stat.label} size="lg" {...stat} />
            ))}
          </div>
          <div className="landing-stats-foot">
            END-TO-END — faulty code refused, corrected code passed. Blind run over 3 random seeds: 3
            true positives, 6 true negatives, 0 false positives, 0 false negatives.
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-inner">
          <div className="landing-section-head">
            <span className="landing-section-num">03</span>
            <span className="landing-section-kicker">TESTS DESIGNED TO FOOL IT</span>
          </div>
          <h2 className="landing-h2 landing-h2--tight">Three traps. None flagged.</h2>
          <p className="landing-lead landing-lead--tight">
            An over-eager detector fires on all three. SYN passed all three, blind.
          </p>

          <div className="landing-traps">
            {data.traps.map((trap) => (
              <div className="landing-trap" key={trap.tag}>
                <div className="landing-trap-head">
                  <span className="landing-trap-tag">{trap.tag}</span>
                  <span className="landing-trap-chip">NOT FLAGGED</span>
                </div>
                <div className="landing-trap-title">{trap.title}</div>
                <div className="landing-trap-body">{trap.body}</div>
                <div className="landing-trap-metric">{trap.metric}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section landing-section--last">
        <div className="landing-closing">
          <div>
            <div className="landing-schematic-label">ARCHITECTURE SCHEMATIC</div>
            <pre className="syn-ascii landing-schematic">{SCHEMATIC}</pre>
          </div>

          <div className="syn-panel">
            <div className="landing-boot-head">
              <span>syn ~ boot</span>
              <span>OPERATIONAL</span>
            </div>
            <div className="landing-boot-body">
              {data.bootLines.slice(0, visibleBootLines).map((line, i) => (
                <div
                  // index keys are correct here: this list only ever grows from
                  // the end and resets, so position identifies the line
                  key={i}
                  className={`landing-boot-line${
                    i === data.bootLines.length - 1 ? ' landing-boot-line--verdict' : ''
                  }`}
                >
                  {line}
                </div>
              ))}
              <div>
                &gt; <span className="syn-cursor">█</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
