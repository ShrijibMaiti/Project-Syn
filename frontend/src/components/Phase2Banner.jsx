/**
 * Marks a view that is a concept, not a capability. It sits above the fold on
 * every unbacked page so nothing below it can be mistaken for a measurement.
 */
export default function Phase2Banner() {
  return (
    <div className="phase2-banner">
      <span className="phase2-banner-chip">NOT BUILT</span>
      <span className="phase2-banner-text">
        Roadmap concept. Nothing on this page is connected to a probe, a measurement, or a verdict.
        Every number below is illustrative placeholder, not a result.
      </span>
    </div>
  );
}
