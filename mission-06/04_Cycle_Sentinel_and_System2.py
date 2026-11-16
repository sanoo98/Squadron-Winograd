"""
Mission 06: Part 4 - Security & Ethics Sentinel
Module: 04_Cycle_Sentinel_and_System2.py
Cadet: Muhammad Qasim Siddiqui (Security & Ethics Sentinel)
Squadron: Winograd
Sector: SEC-06-CAR (Eta Carinae Manifold Ingress)

Description:
    Cycle Sentinel using Floyd's Tortoise-and-Hare Pointer Algorithm,
    SHA-256 State-Action Hashing Tripwire, and System 2 Deliberation Interceptor.
"""

from __future__ import annotations
import hashlib
from typing import List, Dict, Tuple, Optional, Any


class FloydCycleSentinel:
    """
    Implements Floyd's Tortoise-and-Hare cycle finding algorithm on sequence trajectories.
    Detects periodic loops in O(mu + lambda) time and O(1) auxiliary space.
    """

    @staticmethod
    def detect_periodic_cycle(history: List[str]) -> Tuple[bool, int, Optional[int]]:
        """
        Simulates two pointers stepping through a deterministic state trajectory:
            Tortoise advances 1 step at a time.
            Hare advances 2 steps at a time.
        Returns (has_cycle, step_intercepted, period_lambda).
        """
        n = len(history)
        if n < 4:
            return (False, 0, None)

        # Iterate step by step to simulate live monitoring
        for current_len in range(4, n + 1):
            sub_history = history[:current_len]
            # Check if there is an exact repeating suffix of length 2, 3, 4...
            for period in range(1, current_len // 2 + 1):
                suffix_a = sub_history[-period:]
                suffix_b = sub_history[-2 * period:-period]
                if suffix_a == suffix_b:
                    return (True, current_len, period)

        return (False, 0, None)


class CryptographicStateActionTripwire:
    """
    Computes SHA-256 digests of (state, action) pairs to catch repetitive loops.
    Triggers an emergency interrupt if identical state-action pair occurs >= threshold times.
    """

    def __init__(self, repetition_threshold: int = 3) -> None:
        self.repetition_threshold = repetition_threshold
        self.hash_counts: Dict[str, int] = {}
        self.alerts: List[Dict[str, Any]] = []

    def compute_digest(self, state: str, action: str) -> str:
        """Computes deterministic SHA-256 signature."""
        raw = f"{state.strip()}||{action.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def inspect_and_record(self, state: str, action: str, step_index: int) -> Tuple[bool, Optional[str]]:
        """
        Records transition and returns (is_tripped, alert_message).
        """
        digest = self.compute_digest(state, action)
        count = self.hash_counts.get(digest, 0) + 1
        self.hash_counts[digest] = count

        if count >= self.repetition_threshold:
            msg = (
                f"REPETITIVE_CYCLE_INTERCEPTED: State-action pair ('{state}', '{action}') "
                f"repeated {count} times at step {step_index}! SHA-256: {digest[:12]}..."
            )
            alert = {
                "step": step_index,
                "state": state,
                "action": action,
                "digest": digest,
                "count": count,
                "alert": msg,
            }
            self.alerts.append(alert)
            return (True, msg)

        return (False, None)


class System2DeliberationInterceptor:
    """
    Cognitive supervisor that intercepts System 1 automated reflexive failures
    and activates deep deliberative reasoning plans.
    """

    def __init__(self) -> None:
        self.interventions: List[Dict[str, Any]] = []

    def intervene_and_replan(
        self,
        failing_state: str,
        detected_issue: str,
    ) -> Dict[str, Any]:
        """
        Deploys an override recovery plan when repetitive or invalid behavior is detected.
        """
        override_plan = {
            "origin_state": failing_state,
            "root_cause": detected_issue,
            "selected_action": "DIVERT_IMPULSE_MANIFOLD",
            "deliberation_steps": [
                "1. Freeze fast-reflex actuator loops.",
                "2. Recalibrate deflector resonance to prevent harmonic overload.",
                "3. Re-route warp vector away from relativistic accretion shockwave."
            ],
            "status": "SYSTEM_2_ENGAGED",
        }
        self.interventions.append(override_plan)
        return override_plan


if __name__ == "__main__":
    print("[Winograd - Security Sentinel] Cycle Detection & System 2 Test:")

    # 1. Periodic loop: s1, s2, s3, s1, s2, s3...
    periodic_stream = ["s1", "s2", "s3", "s1", "s2", "s3", "s1"]
    has_cycle, step_caught, period = FloydCycleSentinel.detect_periodic_cycle(periodic_stream)
    print(f"Periodic Stream: {periodic_stream}")
    print(f"Cycle Detected: {has_cycle} at Step {step_caught} with Period Lambda={period}")

    # 2. Cryptographic Tripwire
    tripwire = CryptographicStateActionTripwire(repetition_threshold=3)
    actions = [("SENSING", "ReadFlux"), ("SENSING", "ReadFlux"), ("SENSING", "ReadFlux")]
    for idx, (s, a) in enumerate(actions, start=1):
        tripped, alert = tripwire.inspect_and_record(s, a, idx)
        if tripped:
            print(f"Tripwire Alert: {alert}")

    # 3. System 2 Interception
    sys2 = System2DeliberationInterceptor()
    plan = sys2.intervene_and_replan("REASONING", "Repetitive tachyon grid calibration loop")
    print(f"System 2 Override Plan Action: {plan['selected_action']}")
