# SYN

**The guardian of the production manifold.** SYN measures the physical laws of a
codebase — its scaling law and its capacity curve — and refuses merges that
introduce structural collapse.

> It doesn't guess. It measures. **We find the cliff without going over it.**

---

## The proof

| | Result |
|---|---|
| **Blind detection** | **100%** across 3 random seeds — TP=3, FP=0, TN=6, FN=0 |
| **Complexity lens** | O(n²) recovered at exponent ≈ 2.0; O(n) faults cleared |
| **Stability lens** | κ > 0 detected at p ≈ 10⁻⁵ on a live contended service |
| **End-to-end gate** | Faulty → REFUSE, fixed → PASS, enforced by exit code |

Validated against negatives built specifically to fool it — an O(n log n) sort,
an N+1 query pattern (a *real* fault, but linear), and pure linear contention.
None were flagged.

---

## Try it: break the code, watch SYN refuse it

**Live dashboard:** https://YOUR-PROJECT.vercel.app — every run on it was
measured on a GitHub Actions runner, by the workflow in this repo, for a real
commit. Nothing on it is typed in by hand.

The gate protects [`sample_app/checkout.py`](sample_app/checkout.py)
(manifest: [`syn.ci.json`](syn.ci.json)). It ships healthy, so `main` passes.
Each fault is one line away:

| Lens | Change in `sample_app/checkout.py` | SYN's answer |
|---|---|---|
| Stability | `ContendedDB(coherency_k=0.0)` → `ContendedDB(coherency_k=1e-4)` | **REFUSED**: κ ≈ 1e-2, throughput collapses past N ≈ 10 |
| Complexity | `return build_order_report_fixed(n)` → `return build_order_report(n)` | **REFUSED**: growth exponent ≈ 2.0 |

1. Fork this repo, make one of the edits above (the GitHub web editor is fine)
   and open a pull request against this repo.
2. The **SYN gate** check measures your commit on the runner (about 2–4 minutes)
   and fails the check with a certificate in the job summary.
3. The **SYN publish** workflow comments the certificate on your PR and adds the
   run to the live dashboard as `pr-<number>-<sha>`. Open the dashboard's
   Verdict page and pick your run; Stability, Complexity, Evidence, Sensitivity
   and Risk Map all show that run's measurements. (The data refreshes within
   about 5 minutes.)

Notes, stated plainly:
- A first-time contributor's PR needs a maintainer to approve the workflow run
  (GitHub's default for forks). A PR from a branch in this repo runs immediately.
- The runner measures the code in CI, not in production — that is SYN's model:
  a merge gate from bounded, safe measurements.
- A PR can edit the gate itself. In real use, pin the gate to a trusted ref. The
  publish step never runs PR code: it validates the run artifact as data and
  only lets a PR publish its own run.

---

## Two lenses, two axes

Scaling in **input size** and scaling in **concurrency** are different physics
and need different instruments.

| Lens | Axis | Detects |
|---|---|---|
| **Complexity** | input size *n* | Algorithmic detonation — O(nˣ) |
| **Stability** | concurrency *N* | Metastable collapse — coherency cost κ |

Neither lens requires inducing a failure. SYN measures bounded, safe operating
points and derives where the cliff is.

---

## Quickstart

```bash
pip install -e ".[dev]"            # add ",twin" for the PyTorch Twin checks

python tests/check_14_blind.py     # blind detection — the integrity proof
python -m gateway.ci_gate          # run the merge gate (exit 1 = refused)
```

Declare what to probe in `syn.json`:

```json
{
  "syn": {
    "complexity": [
      {"name": "order_report",
       "target": "sample_app.order_service:build_order_report",
       "n_min": 20, "n_max": 12000, "points": 10}
    ],
    "stability": [
      {"name": "db_access",
       "target": "sample_app.contended_db:CONTENDED_DB.call"}
    ]
  }
}
```

**Exit codes:** `0` allowed · `1` refused · `2` gate could not run.
Exit 2 is distinct on purpose — a gate that fails to run must never be read as
approval.

---

## CI

Two workflows (`.github/workflows/`):

- **`syn.yml` — SYN gate** (read-only). On every PR and push to `main`:
  calibrates this runner's noise floor, measures `syn.ci.json`, and fails the
  check when the verdict is REFUSED. Exit `0` allowed · `1` refused · `2` could
  not run. Installs only `requirements-ci.txt` (no PyTorch).
- **`syn-publish.yml` — SYN publish** (`workflow_run`, write access, never runs
  PR code). Validates the run artifact, commits it to the `syn-runs` branch,
  exports every API response as static JSON (`gateway/export_static.py`), and
  comments the certificate on the PR.

Run it manually with **Actions → SYN gate → Run workflow**, ticking
*seed_demos* to re-measure the four demo runs (faulty / clean / warn / unknown)
and blind detection on the runner.

The dashboard reads the published JSON directly — no server:

```bash
cd frontend
VITE_DATA_BASE_URL=https://raw.githubusercontent.com/<owner>/<repo>/syn-runs/api npm run build
```

Against a live API instead: `uvicorn gateway.api:app` and
`VITE_API_BASE_URL=http://localhost:8000/api`.

Locally, the same gate:

```bash
python -m gateway.ci_run --manifest syn.ci.json --run-id local-1 --out-dir syn-out --calibrate
```

---

## How it works

**Complexity** — sweep a callable across log-spaced input sizes with median-of-k
timing, recover the scaling law with two independent selectors, and gate on
*superlinearity* rather than a class label. Below two decades of range, report
insufficient evidence rather than guessing.

**Stability** — measure latency at bounded concurrency levels and test for
evidence of coherency cost by nested F-test:

```
M0:  R = base·(1 + σ(n−1))                  no coherency
M1:  R = base·(1 + σ(n−1) + κ·n(n−1))       coherency
```

κ > 0 means throughput is retrograde, which means a separatrix exists — and its
location follows analytically. No collapse is ever induced.

---

## Documentation

- **[BLUEPRINT.md](BLUEPRINT.md)** — the full engineering record: the failure
  narrative, the three category errors that killed earlier designs, the build
  sequence, and the Claims Discipline table.

## Scope

SYN validates **classification**: given candidate targets, which are risky.
Selecting candidates automatically in a large repository is graph analysis,
deferred to Phase 2. Verdicts are statistical early warnings with stated
p-values — not proofs.
