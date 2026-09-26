"""Static dependency graph of the code under the gate, with measured results overlaid.

This is the REAL half of the Structural Risk Map concept. The structure comes
from the source itself: every function, class and method in the packages the
manifest points at, and every call between them that static analysis can
resolve. Measured results are placed only on the nodes that were actually
probed. Everything else is drawn as NOT MEASURED -- this module never invents
a margin for code SYN did not measure.

Blast radius is graph reachability: every node, and every HTTP route, that
transitively calls a flagged node. Unlike a margin, it needs no measurement --
it is a fact about the code.

INSTANCES. Two module-level instances of one class (CONTENDED_DB, CLEAN_DB)
share a method node, but every edge records which instance it went through, so
a probe of one instance never lends its verdict to callers of the other.

LIMITS OF STATIC ANALYSIS, stated rather than hidden: calls made through
getattr, dynamic dispatch, dependency injection or string lookups are invisible
here, so a blast radius is a lower bound. Resolution is conservative: an edge
is drawn only when the callee resolves to a definition inside the graph.
"""
from __future__ import annotations
import ast
import os
from collections import deque
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "head", "options",
                 "route", "api_route", "websocket"}
SKIP_DIRS = {"__pycache__", ".venv", "venv", "node_modules", "tests", ".git"}


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def _modules(project_root: str, packages: Iterable[str]) -> Dict[str, str]:
    """{dotted.module: path} for every .py file inside the given packages."""
    out: Dict[str, str] = {}
    for pkg in packages:
        pkg_dir = os.path.join(project_root, *pkg.split("."))
        if os.path.isfile(pkg_dir + ".py"):
            out[pkg] = pkg_dir + ".py"
            continue
        for dirpath, dirnames, filenames in os.walk(pkg_dir):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for fn in sorted(filenames):
                if not fn.endswith(".py"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fn), project_root)
                mod = rel[:-3].replace(os.sep, ".")
                if mod.endswith(".__init__"):
                    mod = mod[: -len(".__init__")]
                out[mod] = os.path.join(dirpath, fn)
    return out


class _ModuleIndex:
    """Definitions and name bindings of one module."""

    def __init__(self, name: str, path: str, tree: ast.Module):
        self.name, self.path, self.tree = name, path, tree
        self.defs: Dict[str, ast.AST] = {}          # local name -> def node (top level)
        self.methods: Dict[str, Dict[str, ast.AST]] = {}
        self.imports: Dict[str, str] = {}           # alias -> "module" or "module:name"
        self.instances: Dict[str, str] = {}         # NAME -> local class name it instantiates
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.defs[node.name] = node
            elif isinstance(node, ast.ClassDef):
                self.defs[node.name] = node
                self.methods[node.name] = {
                    b.name: b for b in node.body
                    if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef))}
            elif isinstance(node, ast.Import):
                for a in node.names:
                    self.imports[a.asname or a.name.split(".")[0]] = (
                        a.name if a.asname else a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                for a in node.names:
                    self.imports[a.asname or a.name] = f"{node.module}:{a.name}"
            elif isinstance(node, ast.ImportFrom) and node.level > 0:
                base = name.split(".")
                base = base[: len(base) - node.level] if node.level <= len(base) else []
                mod = ".".join(base + ([node.module] if node.module else []))
                for a in node.names:
                    self.imports[a.asname or a.name] = f"{mod}:{a.name}"
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                val = node.value
                if isinstance(val, ast.Call):
                    callee = val.func
                    cls = (callee.id if isinstance(callee, ast.Name) else
                           callee.attr if isinstance(callee, ast.Attribute) else None)
                    for t in targets:
                        if isinstance(t, ast.Name) and cls:
                            self.instances[t.id] = cls


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #

class CodeGraph:
    def __init__(self, project_root: str, packages: List[str]):
        self.project_root = project_root
        self.packages = packages
        self.index: Dict[str, _ModuleIndex] = {}
        self.parse_errors: List[Dict[str, str]] = []
        for mod, path in _modules(project_root, packages).items():
            try:
                with open(path, encoding="utf-8-sig") as fh:
                    self.index[mod] = _ModuleIndex(mod, path, ast.parse(fh.read(), path))
            except (SyntaxError, UnicodeDecodeError, OSError) as exc:
                self.parse_errors.append({"module": mod, "error": str(exc)})
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: Set[Tuple[str, str, str, str]] = set()
        self._via: Optional[str] = None
        self._collect_nodes()
        self._collect_edges()

    # -- nodes -------------------------------------------------------------- #
    def _collect_nodes(self):
        for mod, ix in self.index.items():
            rel = os.path.relpath(ix.path, self.project_root).replace(os.sep, "/")
            for name, node in ix.defs.items():
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                nid = f"{mod}:{name}"
                self.nodes[nid] = {"id": nid, "module": mod, "name": name, "kind": kind,
                                   "file": rel, "line": node.lineno, "route": None}
                if kind == "function":
                    route = self._route_of(node)
                    if route:
                        self.nodes[nid]["route"] = route
                for mname, mnode in ix.methods.get(name, {}).items():
                    mid = f"{mod}:{name}.{mname}"
                    self.nodes[mid] = {"id": mid, "module": mod, "name": f"{name}.{mname}",
                                       "kind": "method", "file": rel, "line": mnode.lineno,
                                       "route": None}

    @staticmethod
    def _route_of(fn: ast.AST) -> Optional[str]:
        for dec in getattr(fn, "decorator_list", []):
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) \
                    and dec.func.attr in ROUTE_METHODS:
                path = (dec.args[0].value if dec.args and isinstance(dec.args[0], ast.Constant)
                        and isinstance(dec.args[0].value, str) else "")
                verb = dec.func.attr.upper() if dec.func.attr not in ("route", "api_route") else "ANY"
                return f"{verb} {path}".strip()
        return None

    # -- resolution --------------------------------------------------------- #
    def _resolve_symbol(self, ref: str) -> Optional[str]:
        """'pkg.mod:Name' or 'pkg.mod' -> node id / module marker."""
        if ":" not in ref:
            return f"module::{ref}" if ref in self.index else None
        mod, name = ref.split(":", 1)
        if f"{mod}.{name}" in self.index:                 # `from pkg import module`
            return f"module::{mod}.{name}"
        ix = self.index.get(mod)
        if ix is None:
            return None
        if name in ix.defs:
            return f"{mod}:{name}"
        if name in ix.instances:                          # a module-level instance
            return f"instance::{mod}:{ix.instances[name]}@{mod}:{name}"
        if name in ix.imports:                            # re-export
            return self._resolve_symbol(ix.imports[name])
        return None

    def _class_id(self, marker: str) -> Optional[str]:
        """instance::mod:LocalClass@mod:NAME -> the class node id (following
        imports). Records WHICH instance was used in self._via, so two instances
        of one class (CONTENDED_DB vs CLEAN_DB) keep separate blast radii."""
        body, _, inst = marker[len("instance::"):].partition("@")
        if inst:
            self._via = inst
        mod, cls = body.split(":", 1)
        ix = self.index.get(mod)
        if ix is None:
            return None
        if cls in ix.defs and isinstance(ix.defs[cls], ast.ClassDef):
            return f"{mod}:{cls}"
        if cls in ix.imports:
            r = self._resolve_symbol(ix.imports[cls])
            return r if r and r in self.nodes and self.nodes[r]["kind"] == "class" else None
        return None

    def _resolve_expr(self, ix: _ModuleIndex, expr: ast.AST, cls_ctx: Optional[str]
                      ) -> Optional[str]:
        # Name
        if isinstance(expr, ast.Name):
            n = expr.id
            if n in ix.defs:
                return f"{ix.name}:{n}"
            if n in ix.instances:
                return self._class_id(f"instance::{ix.name}:{ix.instances[n]}@{ix.name}:{n}")
            if n in ix.imports:
                r = self._resolve_symbol(ix.imports[n])
                if r and r.startswith("instance::"):
                    return self._class_id(r)
                return r if r in self.nodes else None
            return None
        # Attribute: X.attr
        if isinstance(expr, ast.Attribute):
            attr, base = expr.attr, expr.value
            if isinstance(base, ast.Name) and base.id in ("self", "cls") and cls_ctx:
                mid = f"{ix.name}:{cls_ctx}.{attr}"
                return mid if mid in self.nodes else None
            target = self._resolve_base(ix, base)
            if target is None:
                return None
            if target.startswith("module::"):
                mod = target[len("module::"):]
                r = self._resolve_symbol(f"{mod}:{attr}")
                if r and r.startswith("instance::"):
                    return self._class_id(r)
                return r if r in self.nodes else None
            if target in self.nodes and self.nodes[target]["kind"] == "class":
                mid = f"{target}.{attr}"
                return mid if mid in self.nodes else None
        return None

    def _resolve_base(self, ix: _ModuleIndex, base: ast.AST) -> Optional[str]:
        """Resolve the object an attribute is read from: a module or a class."""
        if isinstance(base, ast.Name):
            n = base.id
            if n in ix.instances:
                return self._class_id(f"instance::{ix.name}:{ix.instances[n]}@{ix.name}:{n}")
            if n in ix.defs and isinstance(ix.defs[n], ast.ClassDef):
                return f"{ix.name}:{n}"
            if n in ix.imports:
                r = self._resolve_symbol(ix.imports[n])
                if r and r.startswith("instance::"):
                    return self._class_id(r)
                return r
            return None
        if isinstance(base, ast.Attribute):                 # pkg.mod.attr chains
            parts = []
            cur = base
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                head = self._resolve_base(ix, cur)
                if head and head.startswith("module::"):
                    dotted = ".".join([head[len("module::"):]] + list(reversed(parts)))
                    if dotted in self.index:
                        return f"module::{dotted}"
                    mod, name = dotted.rsplit(".", 1)
                    r = self._resolve_symbol(f"{mod}:{name}")
                    if r and r.startswith("instance::"):
                        return self._class_id(r)
                    return r
        return None

    # -- edges -------------------------------------------------------------- #
    def _collect_edges(self):
        for mod, ix in self.index.items():
            scopes = [(f"{mod}:{n}", node, None) for n, node in ix.defs.items()
                      if not isinstance(node, ast.ClassDef)]
            for cname, methods in ix.methods.items():
                scopes += [(f"{mod}:{cname}.{m}", node, cname) for m, node in methods.items()]
            for src, fn, cls_ctx in scopes:
                for sub in ast.walk(fn):
                    if not isinstance(sub, ast.Call):
                        continue
                    self._via = None
                    dst = self._resolve_expr(ix, sub.func, cls_ctx)
                    if dst and dst != src:
                        self.edges.add((src, dst, "call", self._via or ""))
                    # callables passed as arguments (callbacks, retries, executors)
                    for arg in list(sub.args) + [k.value for k in sub.keywords]:
                        if isinstance(arg, (ast.Name, ast.Attribute)):
                            self._via = None
                            ref = self._resolve_expr(ix, arg, cls_ctx)
                            if ref and ref != src and self.nodes.get(ref, {}).get("kind") != "class":
                                self.edges.add((src, ref, "ref", self._via or ""))

    # -- public ------------------------------------------------------------- #
    def resolve_target(self, target: str) -> Optional[str]:
        """Manifest target 'pkg.mod:attr[.attr]' -> node id."""
        return self.resolve_target_via(target)[0]

    def resolve_target_via(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        """-> (node id, instance it was reached through or None)."""
        self._via = None
        nid = self._resolve_target(target)
        return nid, (self._via if nid else None)

    def _resolve_target(self, target: str) -> Optional[str]:
        if ":" not in target:
            return None
        mod, path = target.split(":", 1)
        head, _, rest = path.partition(".")
        r = self._resolve_symbol(f"{mod}:{head}")
        if r and r.startswith("instance::"):
            r = self._class_id(r)
        if r is None:
            return None
        if rest:
            mid = f"{r}.{rest}"
            return mid if mid in self.nodes else r
        return r if r in self.nodes else None

    def to_dict(self) -> Dict[str, Any]:
        nodes = sorted(self.nodes.values(), key=lambda n: (n["module"], n["line"]))
        edges = [{"source": s, "target": t, "kind": k, "via": v or None}
                 for s, t, k, v in sorted(self.edges)]
        _layer(nodes, edges)
        return {"packages": self.packages, "nodes": nodes, "edges": edges,
                "entrypoints": [n["id"] for n in nodes if n["route"]],
                "parse_errors": self.parse_errors,
                "stats": {"nodes": len(nodes), "edges": len(edges),
                          "modules": len(self.index),
                          "entrypoints": sum(1 for n in nodes if n["route"])}}


def _layer(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]]) -> None:
    """Assign a drawing layer: shortest call depth from any route. Nodes no
    route reaches get a separate layering from their own roots."""
    out: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    indeg: Dict[str, int] = {n["id"]: 0 for n in nodes}
    for e in edges:
        if e["source"] in out and e["target"] in indeg:
            out[e["source"]].append(e["target"])
            indeg[e["target"]] += 1

    def bfs(starts):
        depth = {s: 0 for s in starts}
        q = deque(starts)
        while q:
            u = q.popleft()
            for v in out[u]:
                if v not in depth:
                    depth[v] = depth[u] + 1
                    q.append(v)
        return depth

    by_id = {n["id"]: n for n in nodes}
    reached = bfs([n["id"] for n in nodes if n["route"]])
    for nid, d in reached.items():
        by_id[nid].update(layer=d, reachable=True)
    rest = [n["id"] for n in nodes if n["id"] not in reached]
    roots = [nid for nid in rest if all(e["target"] != nid or e["source"] not in rest
                                        for e in edges)] or rest
    other = bfs(roots)
    for nid in rest:
        by_id[nid].update(layer=other.get(nid, 0), reachable=False)


def graph_packages(refs: Dict[str, str]) -> List[str]:
    """The top-level packages the manifest's targets live in."""
    pkgs = sorted({r.split(":", 1)[0].split(".")[0] for r in refs.values() if ":" in r})
    return pkgs


def build(project_root: str, refs: Dict[str, str]) -> Tuple[CodeGraph, Dict[str, Any]]:
    g = CodeGraph(project_root, graph_packages(refs))
    return g, g.to_dict()


# --------------------------------------------------------------------------- #
# Overlay + blast radius
# --------------------------------------------------------------------------- #

def overlay(graph: Dict[str, Any], run: Dict[str, Any], refs: Dict[str, str],
            resolve) -> Dict[str, Any]:
    """Place each probe's measured result on its node and compute blast radius.

    `resolve` maps a manifest target string to (node id, instance-or-None).
    When a target is reached THROUGH an instance, the first hop of its blast
    radius only follows calls made through that same instance: CLEAN_DB being
    healthy says nothing about callers of CONTENDED_DB, even though both are the
    same class and share one node."""
    nodes = {n["id"]: n for n in graph["nodes"]}
    callers: Dict[str, List[Tuple[str, Optional[str]]]] = {nid: [] for nid in nodes}
    for e in graph["edges"]:
        if e["target"] in callers:
            callers[e["target"]].append((e["source"], e.get("via")))

    def ancestors(start: str, via: Optional[str]) -> Set[str]:
        first = [src for src, v in callers.get(start, []) if not via or not v or v == via]
        seen, q = set(first), deque(first)
        while q:
            u = q.popleft()
            for v, _ in callers.get(u, []):
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        seen.discard(start)
        return seen

    probes = (run.get("verdict", {}) or {}).get("probes", []) or []
    items = []
    for p in probes:
        ev = p.get("evidence") or {}
        name = ev.get("target")
        ref = refs.get(name)
        nid, via = resolve(ref) if ref else (None, None)
        risk = p.get("risk")
        item = {"lens": p.get("kind"), "target": name, "ref": ref, "node": nid,
                "via": via, "risk": risk, "metric": _metric(p.get("kind"), ev),
                "resolved": nid is not None}
        if nid is None:
            item["reason"] = ("target not found in the manifest recorded with this run"
                              if not ref else "target could not be resolved in the static graph")
        if nid:
            anc = ancestors(nid, via)
            item["callers"] = sorted(anc)
            item["reaching_routes"] = sorted(nodes[a]["route"] for a in anc | {nid}
                                             if nodes.get(a, {}).get("route"))
            if risk in ("refuse", "warn"):
                item["blast_nodes"] = item["callers"]
                item["blast_routes"] = item["reaching_routes"]
        items.append(item)

    measured = {i["node"] for i in items if i["node"]}
    flagged_routes = sorted({r for i in items for r in i.get("blast_routes", [])})
    all_routes = [n["route"] for n in graph["nodes"] if n["route"]]
    return {
        "items": items,
        "stats": {"measured_nodes": len(measured),
                  "coverage_pct": 100.0 * len(measured) / max(len(nodes), 1),
                  "routes_total": len(all_routes),
                  "routes_affected": len(flagged_routes)},
        "routes_affected": flagged_routes,
    }


def _metric(kind: Optional[str], ev: Dict[str, Any]) -> str:
    try:
        if kind == "complexity" and ev.get("exponent") is not None:
            return f"exponent {float(ev['exponent']):.2f}"
        if kind == "stability" and ev.get("kappa") is not None:
            s = f"kappa {float(ev['kappa']):.2e}"
            if ev.get("headroom") is not None:
                s += f", headroom {float(ev['headroom']):.2f}"
            return s
    except (TypeError, ValueError):
        pass
    return ev.get("note") or "no result"
