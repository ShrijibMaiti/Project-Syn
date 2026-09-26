/**
 * The one rule of this system: n and N are different quantities and are never
 * allowed to blur. The distinction is carried by the glyph itself, not only by
 * the label —
 *
 *   n  outlined box · input size  · records processed    · log-log axes
 *   N  filled box   · concurrency · simultaneous requests · linear-N axes
 *
 * Every axis, header and card that names one of them goes through here.
 */

export const AXIS_COPY = {
  n: { title: 'INPUT SIZE', sub: 'RECORDS PROCESSED' },
  N: { title: 'CONCURRENCY', sub: 'SIMULTANEOUS REQUESTS' },
};

export default function AxisLabel({ axis, size = 'lg', title, sub }) {
  const copy = AXIS_COPY[axis];
  const heading = title ?? copy.title;
  const sublabel = sub === undefined ? copy.sub : sub;

  return (
    <div className={`syn-axis syn-axis--${size}`}>
      <span className={`syn-axis-glyph syn-axis-glyph--${axis}`} aria-hidden="true">
        {axis}
      </span>
      {sublabel ? (
        <div>
          <div className="syn-axis-title">{heading}</div>
          <div className="syn-axis-sub">{sublabel}</div>
        </div>
      ) : (
        <span className="syn-axis-title">{heading}</span>
      )}
    </div>
  );
}
