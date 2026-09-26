import { useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import Nav from './components/Nav.jsx';
import Landing from './pages/Landing.jsx';
import Verdict from './pages/Verdict.jsx';
import Stability from './pages/Stability.jsx';
import Complexity from './pages/Complexity.jsx';
import Evidence from './pages/Evidence.jsx';
import BlindDetection from './pages/BlindDetection.jsx';
import StructuralRiskMap from './pages/phase2/StructuralRiskMap.jsx';
import SensitivityHeatmap from './pages/phase2/SensitivityHeatmap.jsx';

export const ROUTES = {
  landing: '/',
  verdict: '/verdict',
  stability: '/stability',
  complexity: '/complexity',
  evidence: '/evidence',
  blind: '/blind',
  riskMap: '/risk-map',
  sensitivity: '/sensitivity',
};

export default function App() {
  const { pathname } = useLocation();

  /**
   * Which probe outcome the data views are showing. Both measurement pages
   * share one switch — a probe run either produced a result or it did not, and
   * the two lenses report that state together.
   */
  const [probeMode, setProbeMode] = useState('ok');

  // The landing page is a full-bleed marketing page: the app chrome only
  // appears once you enter through a CTA.
  const showChrome = pathname !== ROUTES.landing;

  return (
    <div className="syn-app">
      {showChrome && <Nav />}

      <main className="syn-main">
        <div className="syn-main-inner">
          <Routes>
            <Route path={ROUTES.landing} element={<Landing />} />
            <Route path={ROUTES.verdict} element={<Verdict />} />
            <Route
              path={ROUTES.stability}
              element={<Stability mode={probeMode} onModeChange={setProbeMode} />}
            />
            <Route
              path={ROUTES.complexity}
              element={<Complexity mode={probeMode} onModeChange={setProbeMode} />}
            />
            <Route path={ROUTES.evidence} element={<Evidence />} />
            <Route path={ROUTES.blind} element={<BlindDetection />} />
            <Route path={ROUTES.riskMap} element={<StructuralRiskMap />} />
            <Route path={ROUTES.sensitivity} element={<SensitivityHeatmap />} />
            <Route path="*" element={<Navigate to={ROUTES.landing} replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
