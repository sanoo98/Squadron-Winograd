"""
Mission 06: Part 3 - Data & Payload Specialist
Module: 03_MDP_Trajectory_and_Return.py
Cadet: Muhammad Qasim Siddiqui (Data & Payload Specialist)
Squadron: Winograd
Sector: SEC-06-CAR (Eta Carinae Manifold Ingress)

Description:
    Markov Decision Process (MDP) Trajectory Logger, Discounted Return Engine,
    and Empirical Transition Probability Estimator with Heatmap Visualization.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


@dataclass
class MDPStepRecord:
    """Represents a single Markov transition tuple (s_t, a_t, r_t, s_{t+1})."""
    state: str
    action: str
    reward: float
    next_state: str


class MarkovDecisionTrajectoryLogger:
    """Logs trajectory transitions and computes discounted returns and transition distributions."""

    def __init__(self, gamma: float = 0.95) -> None:
        self.gamma = gamma
        self.trajectory: List[MDPStepRecord] = []

    def record_transition(self, state: str, action: str, reward: float, next_state: str) -> None:
        """Appends an MDP transition tuple to the trajectory history."""
        self.trajectory.append(MDPStepRecord(state=state, action=action, reward=reward, next_state=next_state))

    def compute_discounted_return(self, start_idx: int = 0) -> float:
        """
        Computes the discounted return:
            G_t = sum_{k=0}^{T-t} gamma^k * r_{t+k}
        """
        if start_idx >= len(self.trajectory):
            return 0.0

        discounted_sum = 0.0
        for step_offset, record in enumerate(self.trajectory[start_idx:]):
            discounted_sum += (self.gamma ** step_offset) * record.reward
        return discounted_sum

    @staticmethod
    def calculate_discounted_return_from_rewards(rewards: List[float], gamma: float = 0.95) -> float:
        """Utility function to calculate discounted return directly from reward list."""
        g = 0.0
        for t, r in enumerate(rewards):
            g += (gamma ** t) * r
        return g

    def estimate_transition_matrix(self) -> Tuple[np.ndarray, List[str]]:
        """
        Constructs an empirical state-to-state transition probability matrix P(s' | s).
        Returns (matrix, unique_states).
        """
        states = sorted(list(set(
            [step.state for step in self.trajectory] + [step.next_state for step in self.trajectory]
        )))
        state_to_idx = {s: i for i, s in enumerate(states)}
        num_states = len(states)

        counts = np.zeros((num_states, num_states), dtype=np.float64)

        for step in self.trajectory:
            s_idx = state_to_idx[step.state]
            ns_idx = state_to_idx[step.next_state]
            counts[s_idx, ns_idx] += 1.0

        # Row-normalize to get transition probabilities P(s' | s)
        row_sums = counts.sum(axis=1, keepdims=True)
        prob_matrix = np.divide(counts, row_sums, out=np.zeros_like(counts), where=row_sums != 0)

        return prob_matrix, states

    def render_and_save_heatmap(self, output_path: str = "figures/winograd_transition_heatmap.png") -> str:
        """Visualizes and saves the empirical transition matrix as a heatmap."""
        prob_matrix, states = self.estimate_transition_matrix()

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(7, 6))
        cax = ax.imshow(prob_matrix, cmap="mako" if "mako" in plt.colormaps() else "Blues", vmin=0.0, vmax=1.0)
        fig.colorbar(cax, label="Transition Probability P(s' | s)")

        ax.set_xticks(np.arange(len(states)))
        ax.set_yticks(np.arange(len(states)))
        ax.set_xticklabels(states, rotation=45, ha="right", fontsize=9)
        ax.set_yticklabels(states, fontsize=9)
        ax.set_xlabel("Next State (s')", fontweight="bold")
        ax.set_ylabel("Current State (s)", fontweight="bold")
        ax.set_title("Winograd MDP Empirical Transition Probability Heatmap", fontweight="bold", pad=12)

        # Annotate text
        for i in range(len(states)):
            for j in range(len(states)):
                val = prob_matrix[i, j]
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        color="white" if val > 0.5 else "black", fontsize=8)

        plt.tight_layout()
        plt.savefig(out_file, dpi=180)
        plt.close(fig)
        return str(out_file.resolve())


if __name__ == "__main__":
    print("[Winograd - Data Specialist] MDP Trajectory & Discounted Return Test:")
    logger = MarkovDecisionTrajectoryLogger(gamma=0.95)

    # Standard Problem Set Verification: [10, 0, -5, 20] at gamma=0.95
    std_rewards = [10.0, 0.0, -5.0, 20.0]
    expected_g0 = logger.calculate_discounted_return_from_rewards(std_rewards, gamma=0.95)
    print(f"Sequence Rewards: {std_rewards} with gamma=0.95")
    print(f"Calculated Discounted Return G0: {expected_g0:.4f} (Expected: 22.6350)")

    # Simulated flight trajectory
    logger.record_transition("STANDBY", "Init", 10.0, "SENSING")
    logger.record_transition("SENSING", "Analyze", 0.0, "REASONING")
    logger.record_transition("REASONING", "Tune", -5.0, "DISPATCHING")
    logger.record_transition("DISPATCHING", "Verify", 20.0, "EVALUATING")
    logger.record_transition("EVALUATING", "Loop", 5.0, "REASONING")

    matrix, states = logger.estimate_transition_matrix()
    print(f"\nEmpirical States ({len(states)}): {states}")
    print(f"Row sums normalized: {np.sum(matrix, axis=1)}")

    saved_fig = logger.render_and_save_heatmap("Winograd Squad/mission-06/figures/winograd_transition_heatmap.png")
    print(f"Heatmap exported to: {saved_fig}")
