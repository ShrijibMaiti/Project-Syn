"""CI runner: calibrate, gate, store. THE EXIT CODE IS STILL THE GATE.

  0 = merge allowed        1 = merge refused        2 = gate could not run

Differs from `syn-gate` in one way: it also STORES the run (verdict, raw
evidence, code-graph snapshot, and this runner's own noise floor) in
<out-dir>/runs, plus <out-dir>/meta.json. The publish workflow copies that
directory to the `syn-runs` branch, where the static dashboard reads it.

The noise floor is calibrated on the SAME machine that measures, in the same
job: a floor from a laptop would be wrong for a CI runner.

    python -m gateway.ci_run --manifest syn.ci.json --run-id pr-7-abc1234 \
        --out-dir syn-out --calibrate
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import time

EXIT_OK, EXIT_REFUSED, EXIT_ERROR = 0, 1, 2
RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")

# The demo runs shown on the dashboard's landing and verdict pages. Each is a
# real measurement on the runner, stored under a fixed id.
DEMOS = (("syn.json", "demo-faulty"), ("syn_clean.json", "demo-clean"),
         ("syn_warn.json", "demo-warn"), ("syn_unknown.json", "demo-unknown"))


def _exit_code(risk: str, fail_on_warn: bool, fail_on_unknown: bool) -> int:
    if risk == "refuse":
        return EXIT_REFUSED
    if risk == "warn" and fail_on_warn:
        return EXIT_REFUSED
    if risk == "unknown" and fail_on_unknown:
        return EXIT_REFUSED
    return EXIT_OK


def _isolated(code: str) -> str:
    """Run one measurement step in a FRESH interpreter and return its stdout.

    Probes share module-level state (e.g. a ContendedDB's in-flight counter)
    and OS threads; measuring several manifests in one process lets one run
    distort the next. Each step gets its own process, like separate CI jobs."""
    proc = subprocess.run([sys.executable, "-c", code], env=os.environ.copy(),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"step failed ({proc.returncode}): "
                           f"{(proc.stderr or proc.stdout).strip()[-800:]}")
    return proc.stdout.strip()


def _summary(text: str) -> None:
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="syn-ci-run")
    ap.add_argument("--manifest", default="syn.ci.json")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out-dir", default="syn-out")
    ap.add_argument("--calibrate", action="store_true",
                    help="measure this machine's noise floor first (recommended)")
    ap.add_argument("--seed-demos", action="store_true",
                    help="also measure the four demo manifests + blind detection")
    ap.add_argument("--skip-gate", action="store_true",
                    help="only calibrate/seed demos; do not gate the manifest")
    ap.add_argument("--fail-on-warn", action="store_true")
    ap.add_argument("--fail-on-unknown", action="store_true")
    ap.add_argument("--pr-number", default=os.environ.get("SYN_PR_NUMBER", ""))
    ap.add_argument("--sha", default=os.environ.get("GITHUB_SHA", ""))
    ap.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME", "local"))
    args = ap.parse_args(argv)

    if not RUN_ID_RE.match(args.run_id):
        print(f"syn-ci-run: bad --run-id {args.run_id!r}", file=sys.stderr)
        return EXIT_ERROR

    # store.STORE_DIR and the calibration reader both resolve this env var;
    # it must be set BEFORE gateway.store is imported.
    runs_dir = os.path.join(args.out_dir, "runs")
    os.makedirs(runs_dir, exist_ok=True)
    os.environ["SYN_STORE_DIR"] = runs_dir


    meta = {"run_id": args.run_id, "sha": args.sha, "event": args.event,
            "pr_number": int(args.pr_number) if str(args.pr_number).isdigit() else None,
            "manifest": args.manifest, "started_at": time.time(),
            "verdict": None, "exit_code": EXIT_ERROR, "runs": [], "error": None}

    def _finish(code: int) -> int:
        meta["exit_code"] = code
        meta["finished_at"] = time.time()
        with open(os.path.join(args.out_dir, "meta.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2)
        return code

    try:
        if args.calibrate:
            floor = float(_isolated(
                "from gateway.run_and_store import store_calibration;"
                "print(repr(store_calibration()))").splitlines()[-1])
            print(f"syn-ci-run: noise floor on this runner kappa={floor:.3e}")
            meta["kappa_floor"] = floor

        if args.seed_demos:
            for manifest, rid in DEMOS:
                if os.path.exists(manifest):
                    risk = _isolated(
                        "from gateway.run_and_store import run_and_store;"
                        f"v, _ = run_and_store({manifest!r}, {rid!r});"
                        "print(v.risk.value)").splitlines()[-1]
                    meta["runs"].append(rid)
                    print(f"syn-ci-run: demo {rid}: {risk}")
            _isolated("from gateway.run_and_store import store_blind; store_blind()")
            print("syn-ci-run: blind detection stored")

        if args.skip_gate:
            meta["verdict"] = "seeded"
            return _finish(EXIT_OK)

        from gateway.run_and_store import run_and_store
        verdict, cert = run_and_store(args.manifest, args.run_id)
    except (SystemExit, RuntimeError) as exc:
        meta["error"] = str(exc)
        print(f"syn-ci-run: {exc}", file=sys.stderr)
        return _finish(EXIT_ERROR)
    except Exception as exc:
        meta["error"] = f"{type(exc).__name__}: {exc}"
        print(f"syn-ci-run: probe run failed: {meta['error']}", file=sys.stderr)
        return _finish(EXIT_ERROR)

    risk = verdict.risk.value
    meta["verdict"] = risk
    meta["runs"].append(args.run_id)
    with open(os.path.join(args.out_dir, "certificate.md"), "w", encoding="utf-8") as fh:
        fh.write(cert)
    print(cert)

    url = os.environ.get("SYN_DASHBOARD_URL", "").rstrip("/")
    link = f"\n\n**Dashboard:** {url}/verdict?run={args.run_id}" if url else ""
    _summary(cert + link)
    code = _exit_code(risk, args.fail_on_warn, args.fail_on_unknown)
    print(f"syn-ci-run: {args.run_id}: {risk.upper()} -> exit {code}")
    return _finish(code)


if __name__ == "__main__":
    sys.exit(main())
