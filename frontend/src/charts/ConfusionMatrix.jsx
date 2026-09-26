/**
 * Scored after the fact, outside the system, against a ground-truth file SYN
 * never reads. The two correct cells are inverted. An error cell is drawn
 * hollow ONLY when it is zero — a non-zero error cell is the loudest thing on
 * the page, never styled to look empty.
 */
export default function ConfusionMatrix({ confusion, targetCount, seedLabel }) {
  const { truePositive, falsePositive, falseNegative, trueNegative } = confusion;
  const errorCell = (v) =>
    `blind-matrix-cell ${v > 0 ? 'blind-matrix-cell--error' : 'blind-matrix-cell--zero'}`;

  return (
    <div className="syn-panel">
      <div className="blind-panel-head">
        CONFUSION MATRIX — {targetCount} TARGETS
        {seedLabel !== undefined ? ` · SEED ${seedLabel}` : ''}
      </div>
      <div className="blind-matrix-body">
        <div className="blind-matrix">
          <div className="blind-matrix-corner" />
          <div className="blind-matrix-colhead">TRULY RISKY</div>
          <div className="blind-matrix-colhead">TRULY SAFE</div>

          <div className="blind-matrix-rowhead">REFUSED</div>
          <div className="blind-matrix-cell blind-matrix-cell--hit">
            <div className="blind-matrix-num">{truePositive}</div>
            <div className="blind-matrix-label">TRUE POSITIVE</div>
          </div>
          <div className={errorCell(falsePositive)}>
            <div className="blind-matrix-num">{falsePositive}</div>
            <div className="blind-matrix-label">FALSE POSITIVE</div>
          </div>

          <div className="blind-matrix-rowhead">PASSED</div>
          <div className={errorCell(falseNegative)}>
            <div className="blind-matrix-num">{falseNegative}</div>
            <div className="blind-matrix-label">FALSE NEGATIVE</div>
          </div>
          <div className="blind-matrix-cell blind-matrix-cell--hit">
            <div className="blind-matrix-num">{trueNegative}</div>
            <div className="blind-matrix-label">TRUE NEGATIVE</div>
          </div>
        </div>
      </div>
    </div>
  );
}
