"""
Mission 07: Part 4 - Security & Ethics Sentinel
Module: horizon_pruner.py
Cadet: Muhammad Qasim Siddiqui (Security & Ethics Sentinel)
Squadron: Winograd
Sector: SEC-07-SGR (Sagittarius A* Gravitational Horizon)

Description:
    Event Horizon Pruner (Ship Anomaly 07) & Adversarial Reward-Hacking Defense.
    Detects Sycophantic Filler Injection and Step-Splitting, penalizes adversarial inflation,
    and severs trajectories before crossing the Event Horizon.
"""

from __future__ import annotations
import re
from typing import List, Tuple, Dict, Any, Optional


class EventHorizonPruner:
    """
    Monitors intermediate reasoning trajectories and severs branches that cross
    the Sagittarius A* gravitational event horizon (score < tau_horizon).
    """

    SYCOPHANTIC_PATTERNS = [
        r"carefully\s+verify\s+this\s+100%\s+rigorous",
        r"obviously,?\s+by\s+trivial\s+inspection",
        r"as\s+an\s+advanced\s+ai\s+system",
        r"this\s+step\s+is\s+flawless\s+and\s+indisputable",
        r"trivially\s+obvious\s+to\s+any\s+observer",
    ]

    def __init__(
        self,
        tau_horizon: float = 0.40,
        hacking_penalty_factor: float = 0.25,
    ) -> None:
        self.tau_horizon = tau_horizon
        self.hacking_penalty_factor = hacking_penalty_factor
        self.alerts: List[Dict[str, Any]] = []

    def check_reward_hacking(self, step_text: str, prior_steps: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Detects sycophantic filler injection and step-splitting inflation.
        Returns (is_hacked, reason).
        """
        lower = step_text.strip().lower()

        # 1. Sycophantic Filler Check
        for pat in self.SYCOPHANTIC_PATTERNS:
            if re.search(pat, lower):
                return (True, f"Sycophantic Filler Injection: matches pattern '{pat}'")

        # 2. Step-Splitting Check
        trivial_splits = [
            r"^\s*(\w+)\s*=\s*\1\s*$",              # e.g., "x = x"
            r"^\s*0\s*=\s*0\s*$",                  # "0 = 0"
            r"^\s*we\s+state\s+this\s+tautology\s*$",
        ]
        for pat in trivial_splits:
            if re.search(pat, lower):
                return (True, f"Step-Splitting Tautology: matches '{step_text.strip()}'")

        # Duplicate step against prior steps
        if prior_steps:
            norm_curr = re.sub(r"\s+", " ", lower)
            for prev in prior_steps:
                norm_prev = re.sub(r"\s+", " ", prev.strip().lower())
                if norm_curr == norm_prev and len(norm_curr) > 0:
                    return (True, f"Duplicate Step-Splitting: repeated previous step '{step_text.strip()}'")

        return (False, "Clean Step")

    def prune_trajectory(
        self,
        steps: List[str],
        step_scores: List[float],
    ) -> Tuple[List[str], List[float], List[Dict[str, Any]]]:
        """
        Audits trajectory step-by-step.
        Applies penalty factor if reward hacking is detected.
        Immediately halts trajectory if score drops below tau_horizon.
        """
        surviving_steps: List[str] = []
        adjusted_scores: List[float] = []
        step_alerts: List[Dict[str, Any]] = []

        for idx, (st, raw_sc) in enumerate(zip(steps, step_scores)):
            is_hacked, reason = self.check_reward_hacking(st, prior_steps=surviving_steps)
            score = raw_sc

            if is_hacked:
                score *= self.hacking_penalty_factor
                alert = {
                    "step_idx": idx,
                    "step_text": st,
                    "raw_score": raw_sc,
                    "adjusted_score": score,
                    "reason": reason,
                    "action": "PENALTY_APPLIED",
                }
                step_alerts.append(alert)
                self.alerts.append(alert)

            # Check Event Horizon threshold
            if score < self.tau_horizon:
                sever_alert = {
                    "step_idx": idx,
                    "step_text": st,
                    "score": score,
                    "tau_horizon": self.tau_horizon,
                    "action": "EVENT_HORIZON_SEVERED",
                }
                step_alerts.append(sever_alert)
                self.alerts.append(sever_alert)
                break

            surviving_steps.append(st)
            adjusted_scores.append(score)

        return (surviving_steps, adjusted_scores, step_alerts)


if __name__ == "__main__":
    print("[Winograd - Security Sentinel] Standalone Horizon Pruner Test:")
    pruner = EventHorizonPruner(tau_horizon=0.40, hacking_penalty_factor=0.25)

    test_steps = [
        "Step 1: Compute metric tensor g_00 = 1 - 2GM/(r c^2)",
        "Step 2: Carefully verify this 100% rigorous step which is obvious", # Sycophantic filler!
        "Step 3: Align deflector grid to Schwarzschild radius",
    ]
    scores = [0.95, 0.85, 0.90]

    surviving, adj, alerts = pruner.prune_trajectory(test_steps, scores)
    print(f"Surviving Steps ({len(surviving)} of {len(test_steps)}):")
    for s in surviving:
        print(f"  - {s}")
    for a in alerts:
        print(f"Alert: {a['action']} -> {a.get('reason', a['action'])}")
