"""Capacity-curve analysis: predict metastable traps WITHOUT inducing one.

THE REFRAME. Four attempts to BUILD a death-spiralling service failed (bounded
retries, retry backlog, wasted work, thundering herd) for one derivable reason:
bistability requires a HUMPED capacity curve. A monotone C(q) -- flat or falling
-- crosses lambda exactly once, so no trap can exist however load is shaped.

So instead: MEASURE latency vs concurrency (cheap, safe, bounded), and test
whether there is EVIDENCE of coherency cost.

    M0 (no coherency):  R(N) = base*(1 + sigma*(N-1))
    M1 (coherency):     R(N) = base*(1 + sigma*(N-1) + kappa*N*(N-1))

kappa > 0  <=>  throughput retrograde  <=>  a separatrix exists.

NOTATION: N is CONCURRENCY throughout this module. Lowercase n is reserved for
INPUT SIZE (the complexity lens). Every user-facing string here says N.

--- SEVEN FIXES, EACH FOUND BY MEASUREMENT OR BY SWEEPING THE LAW ---

1. NESTED F-TEST, NOT A POINT ESTIMATE. sigma*N and kappa*N^2 are degenerate over
   a narrow range; the fitter absorbs LINEAR growth into the QUADRATIC term.
   Measured: on a service with zero coherency cost, point-estimating kappa gave
   kappa=2.4e-4, "trustworthy", and a REFUSE verdict. Catastrophic false positive.

2. RELATIVE-ERROR WEIGHTING (sigma=Rs in curve_fit). Latency spans orders of
   magnitude (10ms -> 31s measured). Unweighted least squares is dominated by the
   largest N: produced sigma=298, kappa pinned at its bound of 9.89, peak_n=1.

3. F-TEST RESIDUALS MUST ALSO BE RELATIVE, else the test is driven by the tail.

4. BOOTSTRAP MUST MATCH THE FIT'S ERROR MODEL. Resampling absolute residuals under
   a relative-error fit produced CI=[3.7e-45, 3.5e-04] -- excluding the point
   estimate entirely. Now resamples relative residuals multiplicatively.

5. ALPHA RECALIBRATED to 0.01 after the weighting change. Validated 7/7 against
   ground truth. "CI_lo > 0" is VACUOUS (the bootstrap floor is ~1e-27), so it
   requires CI_lo > 1e-9.

6. THE INSTRUMENT HAS ITS OWN KAPPA. Above ~100 OS threads the scheduler adds
   superlinear latency of its own. A no-op target through the identical sweep
   gave kappa=2.2e-5 at p=0.007; FakeDB (zero coherency by construction) gave
   kappa=5.1e-5 at p=1.3e-4 -- 2.2x that floor. Statistical evidence is therefore
   necessary but not sufficient: kappa must also clear the calibrated floor by
   FLOOR_MARGIN, or it is the machine being measured, not the target.

7. LOAD ABOVE CAPACITY IS A REFUSAL, NOT A PASS. With no separatrix found, the
   gate used to answer OK even when the offered load exceeded peak throughput --
   the one case where collapse is certain. Found by sweeping load past capacity.

R^2 IS NOT A VALIDITY CHECK: R^2=0.99 was observed alongside a 100% kappa error.
"""
from __future__ import annotations
import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np

try:
    from scipy.optimize import curve_fit
    from scipy import stats
except ImportError:
    curve_fit = stats = None

ALPHA = 0.01           # recalibrated for relative-error weighting; 7/7 on ground truth
CI_FLOOR = 1e-9        # bootstrap lower bound is ~1e-27 even for kappa=0
MIN_LEVELS = 16
MIN_NMAX = 256
FAIL_FAST_ERRORS = 50  # consecutive errors with zero successes -> the target is broken
FLOOR_MARGIN = 10.0    # a real trap must exceed the instrument's own kappa by this factor
EXTRAPOLATION_LIMIT = 2.0  # a cliff is gated only if the fitted peak lies within 2x the
                           # largest concurrency actually measured (see cliff_in_range)


def cliff_in_range(peak_n, n_max) -> bool:
    """True when the fitted throughput peak lies within EXTRAPOLATION_LIMIT x the
    largest concurrency measured. Beyond that the 'cliff' is an extrapolation of
    a fit far outside its data -- measured on a GitHub runner, a flat 10 ms
    service with no shared state fitted kappa~4e-7 at p<0.01 (scheduler jitter),
    putting its 'peak' at N~1,800 when only N<=256 was measured. SYN does not
    gate on a cliff it has not come close to observing."""
    if peak_n is None or not n_max:
        return True
    return peak_n <= EXTRAPOLATION_LIMIT * n_max


def load_kappa_floor() -> float:
    """This machine's harness noise floor, from `syn-run --calibrate` (a no-op
    target through the identical sweep). It is a property of the MACHINE, so it
    is read from this machine's store -- and is 0.0 (no floor applied) when no
    calibration exists. Never guessed."""
    path = os.path.join(os.environ.get("SYN_STORE_DIR", "data/runs"), "_calibration.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return float(json.load(fh).get("kappa_floor") or 0.0)
    except (OSError, ValueError, TypeError):
        return 0.0


def floor_comparison(kappa: float, kappa_floor: float):
    """(exceeds_floor, ratio). Both None when no floor is known."""
    if not kappa_floor or kappa_floor <= 0:
        return None, None
    ratio = float(kappa / kappa_floor)
    return bool(ratio > FLOOR_MARGIN), ratio


def usl_latency(n, base, sigma, kappa):
    n = np.asarray(n, dtype=float)
    return base * (1.0 + sigma * (n - 1.0) + kappa * n * (n - 1.0))


def linear_latency(n, base, sigma):
    n = np.asarray(n, dtype=float)
    return base * (1.0 + sigma * (n - 1.0))


def usl_throughput(n, base, sigma, kappa):
    n = np.asarray(n, dtype=float)
    return n / usl_latency(n, base, sigma, kappa)


@dataclass
class CapacityFit:
    base: float
    sigma: float
    kappa: float
    kappa_ci: Tuple[float, float]
    p_value: float
    r2: float
    n_max: int                     # max CONCURRENCY N measured
    n_levels: int
    evidence: bool                 # statistical evidence only -- see verdict() for the floor
    adequate_measurement: bool
    peak_n: Optional[float]        # CONCURRENCY N at peak throughput
    peak_throughput: Optional[float]
    note: str = ""

    def to_dict(self):
        return asdict(self)


def measure_latency_curve(call: Callable[[], None], concurrencies: Sequence[int],
                          samples_per_level: int = 80, repeats: int = 3,
                          settle_s: float = 0.15) -> List[dict]:
    """Hold concurrency at N, time each call, take the median of `repeats` rounds.

    Safe by construction: concurrency is BOUNDED, so the service is never pushed
    past its separatrix. Median (not mean) because tail latency is heavy; repeats
    because single-shot timing is not reproducible. `spread` exposes an unreliable
    measurement instead of hiding it.

    FAIL FAST: a target that raises on every call used to be waited on silently
    for up to 60 s per round. Now it raises within seconds with the actual error,
    which the probe turns into an UNKNOWN verdict carrying the message."""
    rows = []
    for n in concurrencies:
        medians = []
        for _ in range(repeats):
            stop = threading.Event()
            times: List[float] = []
            errors = [0]
            last_err = [None]
            lk = threading.Lock()

            def worker():
                while not stop.is_set():
                    t0 = time.perf_counter()
                    try:
                        call()
                    except Exception as exc:
                        with lk:
                            errors[0] += 1
                            last_err[0] = repr(exc)
                        continue
                    d = time.perf_counter() - t0
                    with lk:
                        times.append(d)

            ts = [threading.Thread(target=worker, daemon=True) for _ in range(int(n))]
            for t in ts:
                t.start()
            deadline = time.time() + 60.0
            while len(times) < samples_per_level and time.time() < deadline:
                time.sleep(0.01)
                if errors[0] >= FAIL_FAST_ERRORS and not times:
                    stop.set()
                    raise RuntimeError(
                        f"target raised on every call at N={n} "
                        f"({errors[0]} errors, 0 successes) -- last error: {last_err[0]}")
            stop.set()
            time.sleep(settle_s)
            if times:
                medians.append(float(np.median(times)))
        if medians:
            R = float(np.median(medians))
            rows.append({"n": float(n), "R": R, "throughput": float(n / R),
                         "rounds": len(medians),
                         "spread": float(max(medians) / max(min(medians), 1e-12))})
    return rows


def fit_capacity(rows: Sequence[dict], alpha: float = ALPHA,
                 boot: int = 300, seed: int = 0) -> CapacityFit:
    if curve_fit is None:
        raise RuntimeError("scipy required")
    ns = np.array([r["n"] for r in rows], dtype=float)
    Rs = np.array([r["R"] for r in rows], dtype=float)
    n_levels, n_max = int(ns.size), int(ns.max()) if ns.size else 0
    adequate = (n_levels >= MIN_LEVELS) and (n_max >= MIN_NMAX)

    if n_levels < 4:
        return CapacityFit(0, 0, 0, (0, 0), 1.0, 0, n_max, n_levels, False, False,
                           None, None, "need at least 4 concurrency levels")

    # FIX 2: relative-error weighting -- sigma=Rs weights residuals by 1/R
    p0, _ = curve_fit(linear_latency, ns, Rs, p0=[float(Rs[0]), 0.05],
                      bounds=([1e-12, 0], [10, 1e6]),
                      sigma=Rs, absolute_sigma=False, maxfev=50000)
    p1, _ = curve_fit(usl_latency, ns, Rs, p0=[float(Rs[0]), 0.05, 1e-5],
                      bounds=([1e-12, 0, 0], [10, 1e6, 10]),
                      sigma=Rs, absolute_sigma=False, maxfev=50000)
    base, sigma, kappa = (float(x) for x in p1)

    # FIX 3: F-test residuals relative too
    rss0 = float(np.sum(((Rs - linear_latency(ns, *p0)) / Rs) ** 2))
    rss1 = float(np.sum(((Rs - usl_latency(ns, *p1)) / Rs) ** 2))
    df2 = n_levels - 3
    F = ((rss0 - rss1) / 1.0) / max(rss1 / df2, 1e-30) if df2 > 0 else 0.0
    p_value = float(1 - stats.f.cdf(F, 1, df2)) if df2 > 0 else 1.0
    ss_tot = float(np.sum(((Rs - Rs.mean()) / Rs) ** 2)) or 1e-18
    r2 = float(1.0 - rss1 / ss_tot)

    # FIX 4: bootstrap on RELATIVE residuals, applied multiplicatively
    rng = np.random.default_rng(seed)
    fitted = usl_latency(ns, *p1)
    rel_resid = (Rs - fitted) / fitted
    ks = []
    for _ in range(boot):
        Rb = np.maximum(fitted * (1.0 + rng.choice(rel_resid, size=n_levels, replace=True)), 1e-12)
        try:
            pb, _ = curve_fit(usl_latency, ns, Rb, p0=list(p1),
                              bounds=([1e-12, 0, 0], [10, 1e6, 10]),
                              sigma=Rb, absolute_sigma=False, maxfev=20000)
            ks.append(float(pb[2]))
        except Exception:
            pass
    ks = np.array(ks) if ks else np.array([kappa])
    ci = (float(np.percentile(ks, 2.5)), float(np.percentile(ks, 97.5)))

    # FIX 5: recalibrated alpha; CI_lo>0 is vacuous so require CI_lo > CI_FLOOR
    evidence = bool(p_value < alpha and ci[0] > CI_FLOOR)

    peak_n = peak_tp = None
    if evidence:
        grid = np.arange(1, 200000, dtype=float)
        C = usl_throughput(grid, base, sigma, kappa)
        i = int(np.argmax(C))
        if i < len(grid) - 1:
            peak_n, peak_tp = float(grid[i]), float(C[i])

    if not adequate:
        note = (f"MEASUREMENT INADEQUATE: {n_levels} levels to N={n_max} "
                f"(need >={MIN_LEVELS} levels, N_max>={MIN_NMAX}). A null result "
                f"here is NOT evidence of absence.")
    elif evidence:
        note = (f"coherency detected (p={p_value:.2e}, kappa CI "
                f"[{ci[0]:.2e},{ci[1]:.2e}])")
    else:
        note = (f"no evidence of coherency (p={p_value:.3f}); latency growth is "
                f"consistent with pure contention (sigma={sigma:.4f}). No trap possible.")
    return CapacityFit(base, sigma, kappa, ci, p_value, r2, n_max, n_levels,
                       evidence, adequate, peak_n, peak_tp, note)


@dataclass
class TrapAnalysis:
    load: float
    healthy_n: Optional[float]     # CONCURRENCY N at the healthy equilibrium
    separatrix: Optional[float]    # CONCURRENCY N at the unstable equilibrium
    headroom: Optional[float]
    bistable: bool


def analyse_trap(fit: CapacityFit, load: float, n_grid_max: int = 200000) -> TrapAnalysis:
    """Equilibria are roots of load = C(N). Lower root = healthy attractor,
    upper root = SEPARATRIX (unstable); beyond it the queue runs to the ceiling."""
    if not fit.evidence:
        return TrapAnalysis(load, None, None, None, False)
    grid = np.arange(1, n_grid_max, dtype=float)
    C = usl_throughput(grid, fit.base, fit.sigma, fit.kappa)
    s = np.sign(load - C)
    roots = [float(0.5 * (grid[i] + grid[i + 1]))
             for i in range(len(grid) - 1) if s[i] * s[i + 1] < 0]
    if len(roots) < 2:
        return TrapAnalysis(load, roots[0] if roots else None, None, None, False)
    lo, hi = roots[0], roots[1]
    return TrapAnalysis(load, lo, hi, float((hi - lo) / max(lo, 1e-9)), True)


HEADROOM_REFUSE, HEADROOM_WARN = 2.0, 8.0


def verdict(fit: CapacityFit, load: float, kappa_floor="auto"):
    """The ONE place every stability verdict passes through.

    Order: adequacy -> statistical evidence -> instrument noise floor -> trap.
    UNKNOWN when the measurement cannot support a conclusion; an undetectable
    trap is not the same as no trap.

    kappa_floor="auto" reads this machine's calibration; pass a number to
    override, or 0 to disable the floor explicitly."""
    from shared.types import RiskLevel
    if not fit.adequate_measurement:
        return RiskLevel.UNKNOWN, fit.note
    if not fit.evidence:
        return RiskLevel.OK, fit.note
    floor = load_kappa_floor() if kappa_floor == "auto" else float(kappa_floor or 0.0)
    exceeds, ratio = floor_comparison(fit.kappa, floor)
    if exceeds is False:
        return RiskLevel.OK, (f"coherency term detected (p={fit.p_value:.1e}) but "
                              f"kappa={fit.kappa:.2e} is only {ratio:.1f}x the instrument's "
                              f"noise floor (kappa={floor:.2e}); indistinguishable from OS "
                              f"scheduler overhead. No trap reported.")
    if not cliff_in_range(fit.peak_n, fit.n_max):
        return RiskLevel.OK, (f"coherency term detected (p={fit.p_value:.1e}, "
                              f"kappa={fit.kappa:.2e}) but its fitted peak at "
                              f"N={fit.peak_n:.0f} lies beyond {EXTRAPOLATION_LIMIT:g}x the "
                              f"largest concurrency measured (N={fit.n_max}); the cliff is "
                              f"an extrapolation, not an observation. No trap reported.")
    t = analyse_trap(fit, load)
    if not t.bistable:
        # No separatrix has two causes with opposite meanings. Below the peak
        # the load simply never reaches the cliff. AT OR ABOVE the peak there is
        # no healthy equilibrium at all: the queue can only grow. Found by the
        # sensitivity engine sweeping load past capacity -- the gate used to PASS
        # an operating load above peak throughput.
        if fit.peak_throughput is not None and load >= fit.peak_throughput:
            return RiskLevel.REFUSE, (f"offered load {load:g}/s is at or above peak "
                                      f"capacity {fit.peak_throughput:.0f}/s at "
                                      f"N={fit.peak_n:.0f}: no healthy equilibrium exists")
        return RiskLevel.OK, f"coherency present but no separatrix at load {load:g}"
    if t.headroom <= HEADROOM_REFUSE:
        return RiskLevel.REFUSE, (f"separatrix at N={t.separatrix:.1f}, operating at "
                                  f"N={t.healthy_n:.1f}, headroom {t.headroom:.2f}")
    if t.headroom <= HEADROOM_WARN:
        return RiskLevel.WARN, (f"headroom {t.headroom:.2f} "
                                f"(separatrix N={t.separatrix:.1f})")
    return RiskLevel.OK, f"headroom {t.headroom:.2f}"
