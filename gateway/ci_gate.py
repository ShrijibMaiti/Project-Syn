"""CI entry point. THE EXIT CODE IS THE GATE.

  0 = merge allowed        1 = merge refused        2 = gate could not run

Exit 2 is distinct ON PURPOSE: "SYN failed to run" must never be mistaken for
"SYN approved". A broken gate that exits 0 is worse than no gate at all."""
from __future__ import annotations
import argparse
import json
import os
import sys

from gateway.manifest_loader import find_manifest, load
from orchestration.main_agent import MainAgent
from shared.types import RiskLevel

EXIT_OK, EXIT_REFUSED, EXIT_ERROR = 0, 1, 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="syn-gate",
        description="SYN merge gate — measured capacity and complexity laws")
    ap.add_argument("--manifest", default=None, help="syn.toml / syn.json (auto-discovered)")
    ap.add_argument("--commit", default=os.environ.get("GITHUB_SHA", "workdir"))
    ap.add_argument("--fail-on-warn", action="store_true")
    ap.add_argument("--fail-on-unknown", action="store_true",
                    help="treat 'insufficient evidence' as blocking")
    ap.add_argument("--parallel", action="store_true",
                    help="run probes concurrently (only for INDEPENDENT targets -- "
                         "probes share the host and distort each other)")
    ap.add_argument("--out", default=None, help="write the certificate here")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--summary", action="store_true",
                    help="append to GITHUB_STEP_SUMMARY if set")
    args = ap.parse_args(argv)

    path = find_manifest(args.manifest)
    if not path:
        print("syn-gate: no manifest found (syn.toml / syn.json). Nothing to probe.",
              file=sys.stderr)
        return EXIT_ERROR
    try:
        manifest = load(path)
    except Exception as exc:
        print(f"syn-gate: could not load {path}: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if not manifest.complexity and not manifest.stability:
        print(f"syn-gate: {path} declares no targets.", file=sys.stderr)
        return EXIT_ERROR

    try:
        agent = MainAgent(manifest, serialize=not args.parallel)
        verdict, ctx = agent.run(commit=args.commit)
        cert = agent.certificate(verdict, ctx)
    except Exception as exc:
        print(f"syn-gate: probe run failed: {exc}", file=sys.stderr)
        return EXIT_ERROR

    print(cert)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(cert)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(verdict.to_dict(), fh, indent=2, default=str)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if args.summary and summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(cert + "\n")

    if verdict.risk is RiskLevel.REFUSE:
        return EXIT_REFUSED
    if args.fail_on_warn and verdict.risk is RiskLevel.WARN:
        return EXIT_REFUSED
    if args.fail_on_unknown and verdict.risk is RiskLevel.UNKNOWN:
        return EXIT_REFUSED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
