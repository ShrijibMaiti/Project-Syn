import Phase2Banner from '../../components/Phase2Banner.jsx';

/**
 * 🔮 Roadmap concept — needs the dependency graph plus twin gradients.
 * The gradient this view would visualise exists on the twin today; this view
 * of it does not, so nothing below the banner is bound to data.
 */

const SKETCH = `   changed line ──▶ retry_loop.py:88

              ◉                t = 0.00 s
            ◉ · ◉
          ◉ · · · ◉            wave front
        · · · · · · ·

   ∂(collapse energy)/∂(change)
   ┌──────────────────────────────┐
   │ ████████▓▓▓▓▓▒▒▒▒░░░░        │
   └──────────────────────────────┘
    db.py   order_svc  checkout  billing
    0.41    0.28       0.11      0.02`;

const NEEDS = [
  { k: 'REQUIRES', v: 'A twin fitted across the full dependency graph, not a single subsystem.' },
  {
    k: 'BLOCKED ON',
    v: 'Gradient stability at graph scale; today the gradient is computed on one subsystem.',
  },
  { k: 'STATUS', v: 'No implementation. No data binding. Not on the Phase 1 path.' },
];

export default function SensitivityHeatmap() {
  return (
    <div className="syn-page">
      <Phase2Banner />

      <div className="phase2-header">
        <div className="syn-page-kicker">ROADMAP CONCEPT — 07</div>
        <h1 className="syn-page-title">Sensitivity Heatmap</h1>
        <p className="syn-page-lead syn-page-lead--wide">
          Select a changed line and watch an impact wave propagate outward across the dependency
          graph, weighted by the sensitivity gradient the differentiable twin already computes. A
          small change with a large distant effect becomes immediately legible.
        </p>
      </div>

      <div className="phase2-sketch">
        <div className="phase2-sketch-head">
          <span className="phase2-sketch-label">CONCEPT SKETCH</span>
          <span className="phase2-sketch-meta">ASCII MOCKUP — NON-FUNCTIONAL</span>
        </div>
        <pre className="syn-ascii phase2-sketch-art">{SKETCH}</pre>
        <div className="phase2-sketch-caption">
          Intensity encodes ∂(collapse energy)/∂(change). The gradient exists on the twin today; this
          view of it does not.
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
