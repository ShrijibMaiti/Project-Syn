/**
 * One measured number with its label and a one-line qualifier.
 *
 * size: 'lg' landing proof numbers · 'md' blind-detection rates ·
 *       'sm' the strips under the capacity and scaling-law charts.
 */
export default function StatCard({ label, value, note, size = 'sm' }) {
  return (
    <div className={`syn-stat syn-stat--${size}`}>
      <div className="syn-stat-label">{label}</div>
      <div className="syn-stat-value">{value}</div>
      {note ? <div className="syn-stat-note">{note}</div> : null}
    </div>
  );
}
