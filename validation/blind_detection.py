"""THE INTEGRITY HARNESS.

SYN is handed a shuffled, anonymised list of targets and must decide which are
risky. It never sees ground truth; scoring happens afterwards, outside SYN.

This is what separates "we detect the fault we pointed at" from "we detect faults
we were not told about."

ABSTENTIONS ARE SCORED SEPARATELY. When SYN returns UNKNOWN (insufficient
measurement range) that is a refusal to answer, not a wrong answer, and counting
it as a miss misrepresents the failure mode."""
from __future__ import annotations
from typing import List

from orchestration.probes import complexity_probe, stability_probe
from orchestration.targets import ComplexityTarget, StabilityTarget
from shared.types import RiskLevel
from validation.fault_catalog import anonymise, build_catalog
from validation.metrics import score

STAB_LEVELS = [1, 2, 3, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 160, 200, 256]


def run_blind(seed: int = 0, verbose: bool = True,
              stab_samples: int = 25, stab_repeats: int = 2):
    catalog = build_catalog()
    blind, truth = anonymise(catalog, seed=seed)

    results = []
    for b in blind:
        alias = b["alias"]
        if b["kind"] == "complexity":
            # n_min=20 so a 3000-point sweep clears the 2-decade guard.
            t = ComplexityTarget(alias, b["call"], n_min=20, n_max=b["n_max"], points=10)
            r = complexity_probe(t)
            unknown = r.risk is RiskLevel.UNKNOWN
            flagged = bool(r.evidence.get("superlinear")) if r.evidence else False
            detail = (f"exponent={r.evidence.get('exponent'):.2f}"
                      if r.evidence.get("exponent") is not None else "INSUFFICIENT EVIDENCE")
        else:
            t = StabilityTarget(alias, b["call"], levels=STAB_LEVELS,
                                samples_per_level=stab_samples, repeats=stab_repeats)
            r = stability_probe(t)
            unknown = r.risk is RiskLevel.UNKNOWN
            flagged = bool(r.evidence.get("evidence")) if r.evidence else False
            detail = (f"kappa={r.evidence.get('kappa',0):.2e} "
                      f"p={r.evidence.get('p_value',1):.2e}")
        results.append({"alias": alias, "kind": b["kind"], "flagged": flagged,
                        "unknown": unknown, "risk": r.risk.value,
                        "detail": detail, "summary": r.summary})
        if verbose:
            print(f"  {alias} [{b['kind'][:4]}]  flagged={str(flagged):<5}  "
                  f"risk={r.risk.value:<7} {detail}")
    return results, truth


def evaluate(results, truth, verbose: bool = True):
    pairs, rows, unknowns = [], [], 0
    for r in results:
        c = truth[r["alias"]]
        if r.get("unknown"):
            unknowns += 1
            rows.append((r["alias"], c.id, c.is_faulty, r["flagged"], "ABST",
                         r["detail"], c.why))
            continue
        pairs.append((c.is_faulty, r["flagged"]))
        ok = (c.is_faulty == r["flagged"])
        rows.append((r["alias"], c.id, c.is_faulty, r["flagged"],
                     "OK  " if ok else ("MISS" if c.is_faulty else "FP  "),
                     r["detail"], c.why))
    sc = score(pairs)
    if verbose:
        print(f"\n{'alias':<11}{'true identity':<20}{'faulty':<8}{'flagged':<9}"
              f"{'':<6}{'detail':<26}why")
        for alias, cid, tf, fl, mark, detail, why in rows:
            print(f"{alias:<11}{cid:<20}{str(tf):<8}{str(fl):<9}{mark:<6}"
                  f"{detail:<26}{why[:44]}")
        print(f"\n{sc}   abstentions(UNKNOWN)={unknowns}")
        print("  (an abstention is SYN refusing to answer -- not a wrong answer)")
    return sc, rows, unknowns
