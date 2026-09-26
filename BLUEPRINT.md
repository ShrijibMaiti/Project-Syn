# Project SYN

### The Guardian of the Production Manifold

> **Sýn** — the Norse goddess who guards the door of the hall and, at the Thing, is invoked as the formula of legal denial: *"Sýn is set against it."*
>
> Two doors, one name. SYN guards the **door to production**, and when it refuses a merge it does so the way Sýn refuses a charge — **with grounds, not by rule.** The second reading is **synthesis**: the architecture collapses complexity and stability analysis into one synthesized object.
>
> **SYN is the gate. The measured laws are the engine.**

---

## Status — Phase 1 (Intelligence Core): ✅ VALIDATED

| The Proof | Result |
|---|---|
| **Blind detection** | **100%** across 3 random seeds — TP=3, FP=0, TN=6, FN=0 |
| **Complexity lens** | O(n²) recovered at exponent **≈ 2.0**; O(n) faults cleared |
| **Stability lens** | κ > 0 detected at **p ≈ 10⁻⁵** on a live contended service |
| **End-to-end gate** | Faulty → **REFUSE**, fixed → **PASS**, exit code enforced |

**Convention:** ✅ BUILT / VALIDATED · 🔨 PHASE 1 (Core) · 🔮 PHASE 2 (Scale)

---

# 0 · Genesis — The Failure Narrative

*Three approaches were tried and measured before the fourth survived. This section is the argument: every pivot was forced by evidence, not preference.*

### 0.1 Phase I — "The Assistant"

An AI developer-workflow assistant aimed at debugging and review.

**What broke it.** LLMs treat code as text. They are probabilistic pattern-matchers; they cannot prove structural stability or predict systemic collapse under load.

> *"You're using a chatbot to guess at architecture. You aren't using math to prove anything."*

### 0.2 Phase II — "The Moonshot"

A pivot to computational physics: PINNs for deadlocks, Fourier Neural Operators for extrapolation.

**What broke it — three category errors:**

| # | Error |
|---|---|
| 1 | **Deadlocks are discrete, not continuous.** A graph cycle check solves them exactly; a neural network is a downgrade. |
| 2 | **PINNs require a known PDE.** Software has no governing differential equation. |
| 3 | **Operators don't extrapolate across control parameters.** You cannot find a boiling point by observing warm water. |

> *"You're masking a black box with physics words. Your extrapolation is a guess, not a law."*

### 0.3 Phase III — "The Synthesis"

We stopped predicting **events** and started modeling the **object**.

- Not deadlocks → **metastable failures**: the death spiral, a bad *stable* basin of attraction.
- Not extrapolation → **law discovery**: closed-form scaling laws, O(nˣ).
- Not a GNN label → a **Differentiable Digital Twin**: a simulator for sensitivity analysis, ∂Stability/∂Change.

### 0.4 Phase IV — The USL Discovery

Triggering death spirals in live services proved unreliable — Python's GIL and bounded retries defeated every attempt.

> **The breakthrough: you don't need to observe a crash to predict one.**

By measuring the **Capacity Curve** (throughput vs. concurrency) and fitting the **Universal Scalability Law**, we identify the **Coherency Cost (κ)**. If κ > 0, a metastable trap *must* exist.

**We moved from symptom-based detection to law-based prediction.**

---

# 1 · The Problem

Modern architectures suffer from **silent instabilities** — failures invisible to unit tests and staging, which detonate only in production.

**1 · Metastable Failures (Death Spirals)**
A transient trigger pushes the system into a bad, self-sustaining stable state — a retry storm that outlives its own cause.

**2 · Algorithmic Detonation**
A change shifting a path from O(n log n) to O(n²) is invisible at test scale and catastrophic at production scale.

**3 · The Blast-Radius Blindspot**
No developer can compute how a perturbation in a low-level component destabilizes a distant service.

> **The Discriminator** — continuous methods apply **if and only if** the failure is preceded by an observable macroscopic drift. Discrete, precursor-free faults (lock-ordering deadlocks) are **out of scope**, by design and by proof.

---

# 2 · The Solution

SYN transforms a codebase into a **Differentiable Digital Twin** and gates merges on structural evidence.

**The Engine** — a differentiable simulator whose edges carry transfer functions fit to telemetry, enabling the gradient of system behavior with respect to a code change.

### The Two Lenses

**🔨 The Stability Lens**
Measures the Capacity Curve → fits the Universal Scalability Law → detects Coherency Cost (κ) → computes the **separatrix margin**: how close the system sits to the cliff.

**🔨 The Complexity Lens**
Multi-scale telemetry → symbolic regression → extracts the closed-form scaling law → identifies **detonation points** where that law crosses a resource ceiling.

**The Output** — an evidence-backed verdict with a stated p-value. If the manifold curvature indicates a trap, or the scaling law indicates a detonation, SYN refuses the merge and attaches the measurement that justifies it.

---

# 3 · The Tech Stack

| Layer | Implementation |
|---|---|
| **Synthesis / Twin** | PyTorch + PyTorch Geometric · 🔨 direct-fit simulator on telemetry · 🔮 hypernetwork for generalization |
| **Stability Engine** | USL fit → κ-analysis → separatrix calculation |
| **Complexity Engine** | Symbolic regression for closed-form laws (🔨 analytic basis fit validated; PySR optional) |
| **Orchestration** | Agent mode with parallel subagents |
| **Integration** | FastAPI → CI Gate (GitHub Actions) · 🔮 Redis delta-twinning |

---

# 4 · The Domains

| # | Domain | Role |
|---|---|---|
| **0** | **Shared** ★ | Frozen interface seams — order-state contract, simulator signature, law object |
| **1** | **Telemetry** ★ | Substrate for dataset generation — load drivers, multi-scale sweeps |
| **2** | **Synthesis** | Source → Differentiable Twin |
| **3** | **Stability** | Capacity-curve analysis → κ detection → basin margins |
| **4** | **Complexity** | Scaling-law discovery via symbolic regression |
| **5** | **Orchestration** | Parallel probe coordination → risk aggregation → verdict |
| **6** | **Platform** | API · CI gate · dashboard backend |
| **7** | **Validation** | Integrity harness — blind fault detection |

### Components

```
synthesis/       ast_extractor · graph_builder · simulator (the Twin)
stability/       capacity_curve (USL fit) · basin_detector (separatrix / headroom)
complexity/      symbolic_regressor · detonation_estimator (ceiling crossing)
orchestration/   main_agent (lifecycle) · risk_aggregator (verdict)
validation/      blind_detection_test (the integrity guard)
```

---

# 5 · The Flow

```
  Push
    │
    ▼
  Orchestrator
    │
    ▼
  Synthesis (Twin)
    │
    ├──────────────┬──────────────┐   parallel probes
    ▼              ▼              ▼
  Stability                 Complexity
    │              │              │
    └──────────────┴──────────────┘
                   ▼
            Risk Aggregator
                   ▼
        OK  ·  WARN  ·  REFUSE
```

---

# 6 · The Symmetry — Two Lenses, Two Axes

*This is the distinction most analyses miss: scaling in **input size** and scaling in **concurrency** are different physics, and they need different instruments.*

| Lens | Axis | Variable | Target |
|---|---|---|---|
| **Complexity** | **Input Size** | *n* (records) | **Scaling Law** — O(nˣ) |
| **Stability** | **Concurrency** | *N* (threads) | **Capacity Law** — κ |

---

# 7 · Problems & Solutions

| Problem | Solution |
|---|---|
| **Trivial solutions** in the fit | Relative-error weighting and relative bootstrap for κ |
| **Dimensionality** | Macroscopic order parameters — fixed-dimension aggregate signals |
| **Circular validation** | The **Blind Detection Harness** — faults detected without labels |
| **Isomorphism gap** | Contrastive telemetry alignment — Twin fit against real logs |

---

# 8 · Build Sequence — The Anti-Cheat Order

*Ordered so no step can be faked by hallucinating a later result.*

| # | Step | Why it must come first |
|---|---|---|
| **1** | `shared/` + `sample_app/` | Freeze contracts; stand up the real system under test |
| **2** | `telemetry/` + `validation/blind_detection` | **Write the exam before the student** |
| **3** | `synthesis/` | Build the Differentiable Twin |
| **4** | `stability/` | USL κ-analysis and separatrix detection |
| **5** | `complexity/` | Scaling-law discovery |
| **6** | `orchestration/` | Wire probes into a unified verdict |
| **7** | `platform/` | CI gate and API |

---

# 9 · Claims Discipline

*The conscience of the project. If a sentence isn't in the left column, it doesn't get said.*

| ✅ **Defensible — SAY THIS** | ❌ **Overclaim — DO NOT SAY** |
|---|---|
| "We identify **retrograde capacity** via USL fitting (κ > 0)." | "We predict deadlocks." |
| "We provide an **early warning with a stated p-value**." | "We provide mathematical certainty." |
| "We discover **algorithmic scaling laws** via symbolic regression." | "The neural operator extrapolates to 1M users." |
| "Our lenses separate **input size (n)** from **concurrency (N)**." | "We use one lens for all scaling errors." |
| "Validated via **blind detection** — 100% precision and recall." | "It works because we tested it on the faults." |
| "**κ** for stability, **exponent** for complexity." | "We use an AI to guess the risk." |

---

# 10 · The Proof

### Complexity Lens
Recovered exponent **≈ 2.0** for quadratic faults. Cleared O(n) faults — including an N+1 pattern, a *real* performance fault that is nonetheless linear.

### Stability Lens
Detected **κ > 0** on contended services. Cleared **κ ≈ 0** on monotone services — including pure linear contention, the hardest negative.

### Integrity
**100% blind detection across 3 random seeds.**

```
TP = 3      FP = 0      TN = 6      FN = 0
detection = 100%    false-positive rate = 0%
```

### End-to-End
Correctly discriminated faulty from fixed, with a final **REFUSE** verdict on structural risk and a passing merge on the corrected code.

---

> ## SYN is an evidence-based guardian.
> ### It doesn't guess. It measures the physical laws of the software to prevent structural collapse.
>
> **We find the cliff without going over it.**
