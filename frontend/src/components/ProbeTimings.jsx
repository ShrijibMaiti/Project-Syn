/** Wall-clock cost of each probe in the run, scaled against the slowest one.
 *
 * Defensive on `timings`: the live gate returns a DICT of {probe: seconds} while
 * the fixtures return an array of {name, seconds}. endpoints.js normalises to the
 * array form, but a bad prop must not take the whole page down — it renders empty
 * instead. */
export default function ProbeTimings({ timings, total }) {
  const list = Array.isArray(timings) ? timings : [];
  const slowest = list.reduce((max, t) => Math.max(max, t.seconds ?? 0), 0) || 1;
  const wall =
    total ?? `${list.reduce((acc, t) => acc + (t.seconds ?? 0), 0).toFixed(1)} s`;

  return (
    <div className="syn-panel">
      {list.map((timing) => (
        <div className="verdict-timing-row" key={timing.name}>
          <div style={{ minWidth: 0 }}>
            <div className="verdict-timing-name">{timing.name}</div>
            <div className="syn-meter">
              <div
                className="syn-meter-fill"
                style={{ width: `${(((timing.seconds ?? 0) / slowest) * 100).toFixed(1)}%` }}
              />
            </div>
          </div>
          <div className="verdict-timing-dur">{(timing.seconds ?? 0).toFixed(1)} s</div>
        </div>
      ))}
      <div className="verdict-timing-total">
        <div className="verdict-timing-total-label">TOTAL WALL CLOCK</div>
        <div className="syn-align-right">{wall}</div>
      </div>
    </div>
  );
}