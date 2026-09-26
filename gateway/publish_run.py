"""Merge one CI run artifact into the published `syn-runs` tree, then re-export.

Runs in the PRIVILEGED publish workflow (workflow_run), which has write access
but must never execute code from the pull request. So this treats the artifact
as untrusted DATA: only small, parseable .json files with safe names are
copied, and nothing in it is imported or executed.

    python -m gateway.publish_run --artifact syn-artifact --published published
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import sys

SAFE_NAME = re.compile(r"^_?[A-Za-z0-9._-]{1,80}\.json$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
MAX_FILE = 8 * 1024 * 1024       # a run with a code-graph snapshot is ~100 KB
MAX_FILES = 40
SHARED_BLOBS = {"_calibration.json", "_blind.json"}


class ArtifactError(Exception):
    pass


def _read_json(path: str):
    if os.path.getsize(path) > MAX_FILE:
        raise ArtifactError(f"{os.path.basename(path)} exceeds {MAX_FILE} bytes")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def validate(artifact: str, trusted: bool = False, expect_sha7: str = ""):
    meta_p = os.path.join(artifact, "meta.json")
    if not os.path.isfile(meta_p):
        raise ArtifactError("artifact has no meta.json")
    meta = _read_json(meta_p)
    if not RUN_ID_RE.match(str(meta.get("run_id", ""))):
        raise ArtifactError(f"bad run_id {meta.get('run_id')!r}")
    if not trusted:
        # A pull request controls the code that produced this artifact, so it
        # may only publish its OWN run: pr-<number>-<head sha>, nothing shared.
        rid = meta["run_id"]
        if not re.fullmatch(r"pr-\d{1,7}-[0-9a-f]{7}", rid):
            raise ArtifactError(f"untrusted run_id {rid!r} is not pr-<n>-<sha7>")
        if expect_sha7 and not rid.endswith("-" + expect_sha7):
            raise ArtifactError(f"run_id {rid!r} does not match head sha {expect_sha7}")
        if meta.get("runs") != [rid] or meta.get("verdict") == "seeded":
            raise ArtifactError("an untrusted run may publish only itself")
    runs_dir = os.path.join(artifact, "runs")
    files = []
    if os.path.isdir(runs_dir):
        names = sorted(os.listdir(runs_dir))
        if len(names) > MAX_FILES:
            raise ArtifactError(f"too many files ({len(names)})")
        for n in names:
            p = os.path.join(runs_dir, n)
            if os.path.islink(p) or not os.path.isfile(p) or not SAFE_NAME.match(n):
                raise ArtifactError(f"refusing file {n!r}")
            doc = _read_json(p)
            if not n.startswith("_"):
                # A run file must be named after the run it contains.
                if f"{doc.get('commit')}.json" != n:
                    raise ArtifactError(f"{n} does not match its commit field")
                if doc.get("commit") not in (meta.get("runs") or []):
                    raise ArtifactError(f"{n} is not listed in meta.runs")
            files.append(n)
    return meta, files


def publish(artifact: str, published: str, trusted: bool = False,
            expect_sha7: str = "") -> dict:
    meta, files = validate(artifact, trusted, expect_sha7)
    dest = os.path.join(published, "runs")
    os.makedirs(dest, exist_ok=True)
    for n in files:
        if n.startswith("_") and (n not in SHARED_BLOBS or not trusted):
            continue    # shared blobs come only from trusted (main/dispatch) runs
        shutil.copyfile(os.path.join(artifact, "runs", n), os.path.join(dest, n))

    # Record the run's CI metadata beside it (PR number, sha, exit code).
    ci_dir = os.path.join(published, "ci")
    os.makedirs(ci_dir, exist_ok=True)
    with open(os.path.join(ci_dir, f"{meta['run_id']}.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    os.environ["SYN_STORE_DIR"] = dest
    from gateway.export_static import export
    export(os.path.join(published, "api"))
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="syn-publish-run")
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--published", required=True)
    ap.add_argument("--trusted", action="store_true",
                    help="artifact came from a push/dispatch run on the default branch")
    ap.add_argument("--expect-sha7", default="",
                    help="head sha (7 chars) the run id must end with")
    args = ap.parse_args(argv)
    try:
        meta = publish(args.artifact, args.published, args.trusted, args.expect_sha7)
    except (ArtifactError, ValueError, OSError) as exc:
        print(f"publish_run: rejected artifact: {exc}", file=sys.stderr)
        return 2
    print(f"publish_run: published {meta['run_id']} ({meta.get('verdict')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
