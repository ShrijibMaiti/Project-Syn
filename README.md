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
pip install -e ".[dev]"

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

```yaml
- run: python -m gateway.ci_gate --commit "${GITHUB_SHA}" --summary
```

See `.github/workflows/syn.yml`.

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
