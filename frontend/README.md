# SYN — merge gate front end

React + Vite implementation of the finalised `SYN.dc.html` design from the
Claude Design handoff bundle (`../project/`, with the conversation that produced
it in `../chats/`).

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # → dist/
npm run preview
```

## Layout

```
src/
  api/         client.js (fetch wrapper) · endpoints.js (one call per route) · fixtures.js
  pages/       one per tab, phase2/ for the two unbacked roadmap views
  charts/      hand-built SVG — capacity curve, scaling law, latency, confusion matrix
  components/  Nav, AxisLabel, VerdictBadge, StatCard, EvidenceRow, ProbeTimings, …
  styles/      tokens.css (colour ramp, type, structure) · global.css
```

## Data

`api/endpoints.js` is the only place the views talk to. Each call hits the gate
API when `VITE_API_BASE_URL` is set and otherwise falls back to
`api/fixtures.js` — the captured run the design was built around (commit
`7f3c9a2e1b`). Pages seed their state from the matching fixture and then await
the call, so first paint is instant and live data swaps in as soon as a backend
answers. Point it at a real gate with:

```bash
echo 'VITE_API_BASE_URL=https://gate.example.com/api' > .env.local
```

Expected routes: `/landing`, `/verdict/:state`, `/stability`, `/complexity`,
`/evidence`, `/blind-detection`. The fixture objects are the response shapes.

## Rules the design enforces

These are not cosmetic — they were the point of the design, and changes should
keep them intact:

- **`n` and `N` never blur.** `n` is input size and is always an *outlined*
  glyph on log-log axes; `N` is concurrency and is always a *filled* glyph.
  Everything that names one goes through `components/AxisLabel.jsx`.
- **The four verdicts are visually non-collapsible.** PASS is a white inset bar,
  WARN a dashed frame, REFUSED a fully inverted block, UNKNOWN a diagonal hatch.
  UNKNOWN must never read as an approval.
- **Every data view has all four probe states** (result / measuring /
  insufficient / probe fail). "Insufficient" and "probe fail" each carry an
  explicit *this is not a pass* line.
- **Unbacked views are marked.** `pages/phase2/` sits behind `Phase2Banner`,
  with ASCII concept sketches only — no fake data bound to them.
- **The landing page has no app chrome.** The top bar appears only once you
  enter through a CTA (`App.jsx`).

## Motion

Landing only, and deliberately restrained: the boot log types itself and loops,
a scanline sweeps the ASCII wordmark every 5.5 s, the hero dot-grid drifts one
cell over 18 s, the hero content rises in staggered, and the primary CTA opens
its letter-spacing on hover. All of it respects `prefers-reduced-motion`.
The internal tabs are static by design.

## Fonts

JetBrains Mono and Silkscreen are loaded from Google Fonts in `index.html`. If
you build for a network-restricted environment, self-host them — the layout
assumes a monospace grid.
