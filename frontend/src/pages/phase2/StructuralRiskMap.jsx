import Phase2Banner from '../../components/Phase2Banner.jsx';

/**
 * 🔮 Roadmap concept — needs graph_builder.
 * Nothing here is bound to a probe. The sketch is ASCII on purpose: a
 * rendered-looking chart would imply data that does not exist.
 */

const SKETCH = `        ┌───────────┐
        │  api.gw   │  margin 0.81
        └─────┬─────┘
     ┌────────┴────────┐
┌────┴──────┐   ┌──────┴─────┐
│ order_svc │   │ inventory  │  margin 0.62
└────┬──────┘   └──────┬─────┘
     │   ╲╲╲╲╲╲╲╲╲╲╲   │
     │  ╲╲   WELL   ╲╲ │
     └─ ╲╲  margin  ╲╲─┘
         ╲╲  0.09  ╲╲
          ╲╲╲╲╲╲╲╲╲╲
             ▼ system-state marker

   depth ∝ risk · rim = separatrix`;

const NEEDS = [
  {
    k: 'REQUIRES',
    v: 'Per-node basin detection across the whole graph, not just probed targets.',
  },
  {
    k: 'BLOCKED ON',
    v: 'Automatic candidate selection — the exact thing the blind-detection result does not validate.',
  },
  { k: 'STATUS', v: 'No implementation. No data binding. Not on the Phase 1 path.' },
];

export default function StructuralRiskMap() {
  return (
    <div className="syn-page">
      <Phase2Banner />

      <div className="phase2-header">
        <div className="syn-page-kicker">ROADMAP CONCEPT — 06</div>
        <h1 className="syn-page-title">Structural Risk Map</h1>
        <p className="syn-page-lead syn-page-lead--wide">
          A dependency graph of the codebase rendered as topography. Regions with a shrinking
          stability margin are visually depressed, so a developer sees the shape of their system
          rather than a list of warnings — and sees how close the system-state marker sits to a well
          rim.
        </p>
      </div>

      <div className="phase2-sketch">
        <div className="phase2-sketch-head">
          <span className="phase2-sketch-label">CONCEPT SKETCH</span>
          <span className="phase2-sketch-meta">ASCII MOCKUP — NON-FUNCTIONAL</span>
        </div>
        <pre className="syn-ascii phase2-sketch-art">{SKETCH}</pre>
        <div className="phase2-sketch-caption">
          Depth encodes the stability margin; the rim of a well is the separatrix. No live basin data
          is bound to this sketch.
        </div>
      </div>

      <div className="phase2-needs">
        {NEEDS.map((need) => (
          <div className="phase2-need" key={need.k}>
            <div className="phase2-need-k">{need.k}</div>
            <div className="phase2-need-v">{need.v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
