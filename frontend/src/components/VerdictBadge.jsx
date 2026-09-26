/**
 * The four verdicts are deliberately non-collapsible: each one is a different
 * physical treatment, so no two can be mistaken for one another at a glance or
 * in a screenshot.
 *
 *   PASS     white inset bar
 *   WARN     dashed frame
 *   REFUSED  fully inverted block
 *   UNKNOWN  diagonal hatch — never reads as an approval
 */

const RISK_CHIP = {
  HIGH: 'syn-chip--solid',
  MED: 'syn-chip--dashed',
  LOW: 'syn-chip--outline',
  NONE: 'syn-chip--dashed-dim',
  UNKNOWN: 'syn-chip--dashed-dim', // inconclusive -- styled apart from OK
};

export function RiskChip({ risk }) {
  return <span className={`syn-chip ${RISK_CHIP[risk] || 'syn-chip--faint'}`}>{risk}</span>;
}

export default function VerdictBadge({ state, glyph, summary }) {
  return (
    <div className={`verdict-badge verdict-badge--${state}`}>
      <div className="verdict-badge-label">VERDICT</div>
      <div className="verdict-badge-line">
        <span>{glyph}</span>
        <span>{state}</span>
      </div>
      <div className="verdict-badge-sub">{summary}</div>
    </div>
  );
}
