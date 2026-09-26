"""Risk map on THIS repository: the static call graph of the code the
manifests point at, and where each probe target lands in it.

It asserts only what must hold on any codebase -- every manifest target
resolves to a node, and the graph builds without parse errors -- then prints
the structure so you can read the blast radius of your own code."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from analysis.code_graph import build  # noqa: E402
from analysis.snapshot import manifest_refs  # noqa: E402

checks = []
for manifest in ("syn.json", "syn_clean.json"):
    path = os.path.join(ROOT, manifest)
    if not os.path.exists(path):
        print(f"(skipping {manifest}: not found)")
        continue
    refs = manifest_refs(path)
    g, graph = build(ROOT, refs)
    st = graph["stats"]
    print(f"\n===== {manifest}  packages={graph['packages']}  nodes={st['nodes']}  "
          f"call edges={st['edges']}  routes={st['entrypoints']}")
    for n in graph["nodes"]:
        if n["route"]:
            print(f"  route  {n['route']:24s} -> {n['id']}")
    callers = {}
    for e in graph["edges"]:
        callers.setdefault(e["target"], []).append((e["source"], e.get("via")))

    for name, ref in refs.items():
        nid, via = g.resolve_target_via(ref)
        print(f"\n  {name}: {ref}")
        print(f"     -> node {nid}" + (f"   (through instance {via})" if via else ""))
        if nid:
            seen, stack = set(), [nid]
            first = True
            while stack:
                u = stack.pop()
                for src, v in callers.get(u, []):
                    if first and via and v and v != via:
                        continue
                    if src not in seen:
                        seen.add(src)
                        stack.append(src)
                first = False
            routes = sorted(n["route"] for n in graph["nodes"]
                            if n["route"] and (n["id"] in seen or n["id"] == nid))
            print(f"     callers: {len(seen)}   routes that reach it: {routes or 'none'}")
        checks.append((f"{manifest}: '{name}' resolves to a graph node", nid is not None))
    checks.append((f"{manifest}: every module parsed", not graph["parse_errors"]))
    if graph["parse_errors"]:
        print("  parse errors:", graph["parse_errors"])

print()
for name, ok in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
print("\nRISK MAP GRAPH:", "PASS" if checks and all(ok for _, ok in checks) else "FAIL")
