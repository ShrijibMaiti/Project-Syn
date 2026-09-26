"""Source -> AST facts. Pure stdlib `ast`; no execution of the target code."""
from __future__ import annotations
import ast
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FunctionFact:
    id: str
    module: str
    name: str
    lineno: int
    calls: List[str] = field(default_factory=list)
    loop_depth: int = 0            # max nesting -> complexity prior
    has_recursion: bool = False
    calls_in_loop: List[str] = field(default_factory=list)   # N+1 smell


class _Visitor(ast.NodeVisitor):
    def __init__(self, module: str):
        self.module = module
        self.facts: Dict[str, FunctionFact] = {}
        self._stack: List[FunctionFact] = []
        self._loop = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        fact = FunctionFact(id=f"{self.module}.{node.name}", module=self.module,
                            name=node.name, lineno=node.lineno)
        self.facts[fact.id] = fact
        self._stack.append(fact)
        saved, self._loop = self._loop, 0
        self.generic_visit(node)
        self._loop = saved
        self._stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def _loop_visit(self, node) -> None:
        self._loop += 1
        if self._stack:
            self._stack[-1].loop_depth = max(self._stack[-1].loop_depth, self._loop)
        self.generic_visit(node)
        self._loop -= 1

    visit_For = _loop_visit
    visit_While = _loop_visit
    visit_AsyncFor = _loop_visit

    def visit_Call(self, node: ast.Call) -> None:
        if self._stack:
            fn = node.func
            name = (fn.attr if isinstance(fn, ast.Attribute)
                    else fn.id if isinstance(fn, ast.Name) else None)
            if name:
                cur = self._stack[-1]
                cur.calls.append(name)
                if name == cur.name:
                    cur.has_recursion = True
                if self._loop > 0:
                    cur.calls_in_loop.append(name)
        self.generic_visit(node)


def extract_file(path: str, module: Optional[str] = None) -> Dict[str, FunctionFact]:
    with open(path) as fh:
        tree = ast.parse(fh.read(), filename=path)
    mod = module or os.path.splitext(os.path.basename(path))[0]
    v = _Visitor(mod)
    v.visit(tree)
    return v.facts


def extract_tree(root: str, skip=("venv", ".git", "__pycache__", "node_modules")
                 ) -> Dict[str, FunctionFact]:
    out: Dict[str, FunctionFact] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if fn.endswith(".py"):
                try:
                    out.update(extract_file(os.path.join(dirpath, fn)))
                except SyntaxError:
                    continue
    return out