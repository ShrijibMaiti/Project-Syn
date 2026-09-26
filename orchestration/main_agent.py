"""End-to-end PR check: plan -> parallel subagents -> aggregated verdict."""
from __future__ import annotations
from typing import Tuple

from orchestration.certificate import render_markdown
from orchestration.lifecycle import RunContext, Stage
from orchestration.probes import complexity_probe, stability_probe
from orchestration.risk_aggregator import aggregate
from orchestration.subagents import run_probes
from orchestration.targets import ProbeManifest
from shared.verdict import Verdict


class MainAgent:
    def __init__(self, manifest: ProbeManifest, serialize: bool = False):
        self.manifest = manifest
        self.serialize = serialize

    def run(self, commit: str = "workdir") -> Tuple[Verdict, RunContext]:
        ctx = RunContext(commit=commit).advance(Stage.PROBING)
        probes = {}
        for t in self.manifest.complexity:
            probes[f"complexity:{t.name}"] = (lambda t=t: complexity_probe(t))
        for t in self.manifest.stability:
            probes[f"stability:{t.name}"] = (lambda t=t: stability_probe(t))
        results, timings = run_probes(probes, serialize=self.serialize)
        ctx.timings = timings
        ctx.advance(Stage.AGGREGATING)
        verdict = aggregate(results)
        ctx.advance(Stage.DONE)
        return verdict, ctx

    def certificate(self, verdict: Verdict, ctx: RunContext) -> str:
        return render_markdown(verdict, ctx.commit, ctx.timings)
