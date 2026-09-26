import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

import { getRunMeta } from '../api/endpoints.js';
import pkg from '../../package.json';

/**
 * The app chrome: wordmark + run status, the eight tabs, and the breadcrumb
 * strip — three stacked rows inside one sticky block, so there is no sticky
 * offset to keep in sync.
 */

export const NAV_ITEMS = [
  { to: '/', num: '00', label: 'LANDING', flag: '', slug: 'landing', crumb: 'SYN // MERGE GATE' },
  {
    to: '/verdict',
    num: '01',
    label: 'VERDICT',
    flag: '●',
    slug: 'verdict',
    crumb: '01 // VERDICT CERTIFICATE',
  },
  {
    to: '/stability',
    num: '02',
    label: 'STABILITY',
    flag: 'N',
    slug: 'stability',
    crumb: '02 // CAPACITY CURVE',
  },
  {
    to: '/complexity',
    num: '03',
    label: 'COMPLEXITY',
    flag: 'n',
    slug: 'complexity',
    crumb: '03 // SCALING LAW',
  },
  {
    to: '/evidence',
    num: '04',
    label: 'EVIDENCE',
    flag: '',
    slug: 'evidence',
    crumb: '04 // STATISTICAL EVIDENCE',
  },
  {
    to: '/blind',
    num: '05',
    label: 'BLIND DETECT',
    flag: '',
    slug: 'blind',
    crumb: '05 // BLIND DETECTION',
  },
  {
    to: '/risk-map',
    num: '06',
    label: 'RISK MAP',
    flag: '◇',
    slug: 'riskmap',
    crumb: '06 // STRUCTURAL RISK MAP',
  },
  {
    to: '/sensitivity',
    num: '07',
    label: 'SENSITIVITY',
    flag: '◇',
    slug: 'sensitivity',
    crumb: '07 // SENSITIVITY HEATMAP',
  },
];

export default function Nav() {
  const { pathname, search } = useLocation();
  const current = NAV_ITEMS.find((item) => item.to === pathname);

  // Commit, verdict and recorded time of the run being viewed. Re-read when
  // ?run= changes. Fixture data is flagged as such, never shown as measured.
  const [meta, setMeta] = useState(null);
  useEffect(() => {
    let on = true;
    getRunMeta().then((m) => {
      if (on) setMeta(m);
    });
    return () => {
      on = false;
    };
  }, [search]);

  return (
    <div className="syn-topbar">
      <div className="syn-topbar-row">
        <div className="syn-wordmark-group">
          <span className="syn-wordmark">SYN</span>
          <span className="syn-topbar-sub">MERGE GATE / v{pkg.version}</span>
        </div>
        <div className="syn-topbar-status">
          <span>
            RUN <span className="syn-status-val">{meta ? meta.commit : '…'}</span>
          </span>
          <span>
            VERDICT{' '}
            <span className={meta?.state === 'REFUSED' ? 'syn-status-armed' : 'syn-status-val'}>
              {meta?.state ?? '—'}
            </span>
          </span>
          <span>
            DATA{' '}
            <span className={meta?.live ? 'syn-status-armed' : 'syn-status-val'}>
              {meta ? (meta.live ? 'LIVE' : 'FIXTURE') : '…'}
            </span>
          </span>
        </div>
      </div>

      <nav className="syn-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={{ pathname: item.to, search }}
            end={item.to === '/'}
            className={({ isActive }) => `syn-nav-item${isActive ? ' active' : ''}`}
          >
            <span className="syn-nav-num">{item.num}</span>
            <span className="syn-nav-label">{item.label}</span>
            <span className="syn-nav-flag">{item.flag}</span>
          </NavLink>
        ))}
      </nav>

      <div className="syn-breadcrumb">
        <span className="syn-breadcrumb-crumb">{current ? current.crumb : 'SYN'}</span>
        <span className="syn-breadcrumb-sep">///</span>
        <span className="syn-breadcrumb-path">syn@gate:~/{current ? current.slug : ''}</span>
        <span className="syn-breadcrumb-spacer" />
        <span className="syn-breadcrumb-time">{meta?.timestamp ?? ''}</span>
      </div>
    </div>
  );
}
