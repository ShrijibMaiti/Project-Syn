/**
 * Rows that carry an estimate and the uncertainty attached to it. Nothing in
 * this system states a value without the interval or the p-value beside it.
 */

/** metric · value — the fitted-parameter rows inside a model panel. */
export default function EvidenceRow({ label, value, selected = false }) {
  return (
    <div className={`evidence-row${selected ? ' evidence-row--selected' : ''}`}>
      <span className="evidence-row-k">{label}</span>
      <span className="evidence-row-v">{value}</span>
    </div>
  );
}

/** parameter · estimate · 95% CI · p — one row of the estimates table. */
export function ParameterRow({ name, est, ci, p }) {
  return (
    <div className="evidence-params-row">
      <div className="evidence-param-name">{name}</div>
      <div className="evidence-param-est">{est}</div>
      <div className="evidence-param-ci">{ci}</div>
      <div className="evidence-param-p">{p}</div>
    </div>
  );
}
