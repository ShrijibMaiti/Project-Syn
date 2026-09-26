/**
 * A probe run is in exactly one of four states, and both measurement lenses
 * report it the same way. "Insufficient" and "probe fail" each carry an
 * explicit line saying this is not a pass — that wording is load-bearing.
 */

export const PROBE_MODES = [
  { id: 'ok', label: 'RESULT' },
  { id: 'loading', label: 'MEASURING' },
  { id: 'insufficient', label: 'INSUFFICIENT' },
  { id: 'failed', label: 'PROBE FAIL' },
];

export function ProbeModeSwitch({ mode, onChange }) {
  return (
    <div className="syn-switch-row">
      {PROBE_MODES.map((option) => (
        <button
          key={option.id}
          type="button"
          className={`syn-switch${mode === option.id ? ' active' : ''}`}
          aria-pressed={mode === option.id}
          onClick={() => onChange(option.id)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function MeasuringPanel({ label, lines, percent, foot }) {
  return (
    <div className="syn-measuring">
      <div className="syn-measuring-label">{label}</div>
      <pre className="syn-measuring-log">
        {lines.join('\n')}
        {'\n> '}
        <span className="syn-cursor">█</span>
      </pre>
      <div className="syn-progress-track">
        <div className="syn-progress-fill" style={{ width: `${percent}%` }} />
      </div>
      <div className="syn-measuring-foot">{foot}</div>
    </div>
  );
}

export function ProbeFailurePanel({ log, foot }) {
  return (
    <div className="syn-panel">
      <div className="blind-panel-head">PROBE FAILURE — NO MEASUREMENT TAKEN</div>
      <pre className="syn-failure-log">{log}</pre>
      <div className="syn-panel-foot">{foot}</div>
    </div>
  );
}
