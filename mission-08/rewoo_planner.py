"""
Mission 08: Part 1 - Systems Architect
Module: rewoo_planner.py
Cadet: Hassaan Ahmad Khawaja (Systems Architect)
Squadron: Winograd
Sector: SEC-08-CYG (Cygnus X-1 Accretion Corona)

Description:
    Decoupled ReWOO (Reasoning WithOut Observation) DAG Engine:
    Topological execution levels, symbolic variable substitution (#E1..#EK),
    and Token-Cost Profiler comparing O(K^2) ReAct vs O(K) ReWOO.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable


@dataclass
class PlanStep:
    """Represents a discrete step in the ReWOO blueprint."""
    var_name: str          # e.g., "#E1"
    plan_desc: str         # e.g., "Scan radiation flux in corona"
    tool_name: str         # e.g., "TachyonScanner"
    raw_arg: str           # e.g., "target=Corona"


class ReWOOPlanner:
    """Decoupled DAG planner executing independent tool calls in parallel topological levels."""

    def __init__(self, tool_registry: Optional[Dict[str, Callable[[str], str]]] = None) -> None:
        self.tool_registry: Dict[str, Callable[[str], str]] = tool_registry or {}

    def register_tool(self, name: str, func: Callable[[str], str]) -> None:
        self.tool_registry[name] = func

    def parse_blueprint(self, blueprint_text: str) -> List[PlanStep]:
        """Parses Plan: ... and #E_i = ToolName[raw_arg] syntax."""
        steps: List[PlanStep] = []
        lines = [line.strip() for line in blueprint_text.strip().splitlines() if line.strip()]

        current_plan = ""
        pattern = re.compile(r"^(#E\d+)\s*=\s*(\w+)\[(.*)\]$")

        for line in lines:
            if line.startswith("Plan:"):
                current_plan = line[len("Plan:"):].strip()
            else:
                m = pattern.match(line)
                if m:
                    var, tool, arg = m.groups()
                    step = PlanStep(
                        var_name=var,
                        plan_desc=current_plan or f"Run {tool}",
                        tool_name=tool,
                        raw_arg=arg.strip(),
                    )
                    steps.append(step)
                    current_plan = ""
        return steps

    def build_dependency_levels(self, steps: List[PlanStep]) -> List[List[PlanStep]]:
        """Groups plan steps into topological levels based on variable dependencies (#E1..#EK)."""
        levels: List[List[PlanStep]] = []
        resolved: set = set()
        unprocessed = list(steps)

        while unprocessed:
            current_layer: List[PlanStep] = []
            deferred: List[PlanStep] = []

            for step in unprocessed:
                deps = set(re.findall(r"#E\d+", step.raw_arg))
                if deps.issubset(resolved):
                    current_layer.append(step)
                else:
                    deferred.append(step)

            if not current_layer:
                raise ValueError("Cyclic dependency detected in ReWOO plan blueprint.")

            levels.append(current_layer)
            for s in current_layer:
                resolved.add(s.var_name)
            unprocessed = deferred

        return levels

    def execute_dag(self, steps: List[PlanStep]) -> Dict[str, str]:
        """Executes DAG level by level with variable substitution."""
        levels = self.build_dependency_levels(steps)
        environment: Dict[str, str] = {}

        for level in levels:
            for step in level:
                resolved_arg = step.raw_arg
                for var, val in environment.items():
                    resolved_arg = resolved_arg.replace(var, str(val))

                tool = self.tool_registry.get(step.tool_name)
                if tool is None:
                    environment[step.var_name] = f"ERR_UNKNOWN_TOOL: {step.tool_name}"
                else:
                    try:
                        res = tool(resolved_arg)
                        environment[step.var_name] = str(res)
                    except Exception as err:
                        environment[step.var_name] = f"ERR_EXECUTION_FAILURE: {str(err)}"

        return environment

    @staticmethod
    def compare_token_cost(
        k_steps: int,
        base_tokens: int = 400,
        step_tokens: int = 150,
        obs_tokens: int = 100,
    ) -> Dict[str, Any]:
        """
        Calculates cumulative token consumption:
        ReAct (O(K^2)): C_ReAct = sum_{t=1}^K [L0 + (t-1)*L_step]
        ReWOO (O(K)):   C_ReWOO = 2*L0 + K*(L_step + L_obs)
        """
        react_tokens = 0
        current_ctx = base_tokens
        step_cost = step_tokens + obs_tokens
        for _ in range(k_steps):
            react_tokens += current_ctx
            current_ctx += step_cost

        rewoo_tokens = (2 * base_tokens) + (k_steps * step_cost)

        savings_tokens = react_tokens - rewoo_tokens
        savings_pct = (savings_tokens / float(react_tokens)) * 100.0 if react_tokens > 0 else 0.0
        speedup = react_tokens / float(rewoo_tokens) if rewoo_tokens > 0 else 1.0

        return {
            "k_steps": k_steps,
            "react_tokens": react_tokens,
            "rewoo_tokens": rewoo_tokens,
            "savings_tokens": savings_tokens,
            "savings_pct": savings_pct,
            "speedup_ratio": speedup,
        }


if __name__ == "__main__":
    print("[Winograd - Systems Architect] Standalone ReWOO Planner Test:")
    planner = ReWOOPlanner()
    planner.register_tool("TachyonScanner", lambda arg: f"TachyonScan({arg})")
    planner.register_tool("CoronaModulator", lambda arg: f"CoronaMod({arg})")
    planner.register_tool("VectorSynthesizer", lambda arg: f"VectorSynth({arg})")

    bp = """
    Plan: Analyze Cygnus X-1 X-ray flare radiation
    #E1 = TachyonScanner[sector=CygnusX1]
    Plan: Modulate deflector shields against corona flux
    #E2 = CoronaModulator[source=#E1]
    Plan: Determine safe escape path
    #E3 = VectorSynthesizer[origin=#E1]
    Plan: Synthesize warp vector with calibrated shields
    #E4 = VectorSynthesizer[def=#E2;nav=#E3]
    """

    steps = planner.parse_blueprint(bp)
    levels = planner.build_dependency_levels(steps)
    print(f"Parsed Steps: {len(steps)} | Levels: {len(levels)}")
    for i, lvl in enumerate(levels):
        print(f"  Level {i}: {[s.var_name for s in lvl]}")

    results = planner.execute_dag(steps)
    for k, v in results.items():
        print(f"  {k} -> {v}")

    cost = ReWOOPlanner.compare_token_cost(k_steps=6)
    print(f"\nToken Analysis (K=6): ReAct={cost['react_tokens']} vs ReWOO={cost['rewoo_tokens']} ({cost['savings_pct']:.2f}% savings)")
