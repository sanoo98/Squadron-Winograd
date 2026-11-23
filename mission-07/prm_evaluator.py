"""
Mission 07: Part 3 - Data & Payload Specialist
Module: prm_evaluator.py
Cadet: Muhammad Qasim Siddiqui (Data & Payload Specialist)
Squadron: Winograd
Sector: SEC-07-SGR (Sagittarius A* Gravitational Horizon)

Description:
    Process Reward Model (PRM) Evaluator, Step Reductions (min, prod, geometric_mean),
    ORM False-Positive Trap Demonstration, and Math-Shepherd Monte Carlo Supervision.
"""

from __future__ import annotations
import math
from typing import List, Dict, Any, Tuple


class ProcessRewardEvaluator:
    """Step-level Process Reward Evaluator and trajectory aggregator."""

    @staticmethod
    def reduce_min(step_scores: List[float]) -> float:
        """Weakest link reduction: minimum score along trajectory."""
        return min(step_scores) if step_scores else 0.0

    @staticmethod
    def reduce_prod(step_scores: List[float]) -> float:
        """Joint probability reduction: product of step scores."""
        if not step_scores:
            return 0.0
        val = 1.0
        for s in step_scores:
            val *= s
        return val

    @staticmethod
    def reduce_geometric_mean(step_scores: List[float]) -> float:
        """Length-normalized quality reduction: (prod r_t)^(1/T)."""
        if not step_scores:
            return 0.0
        p = ProcessRewardEvaluator.reduce_prod(step_scores)
        return math.pow(p, 1.0 / len(step_scores))

    def evaluate_trajectory(self, step_scores: List[float]) -> Dict[str, float]:
        """Calculates min, product, and geometric mean across step scores."""
        return {
            "min": self.reduce_min(step_scores),
            "prod": self.reduce_prod(step_scores),
            "geometric_mean": self.reduce_geometric_mean(step_scores),
        }

    @staticmethod
    def math_shepherd_estimation(
        rollout_answers: List[Any],
        ground_truth: Any,
    ) -> Tuple[float, float]:
        """
        Math-Shepherd Monte Carlo Supervision:
            y_soft = (1/M) * sum(I(ans(z) == y*))
            y_hard = 1.0 if y_soft > 0 else 0.0
        """
        if not rollout_answers:
            return (0.0, 0.0)

        correct_count = sum(1 for ans in rollout_answers if ans == ground_truth)
        m = float(len(rollout_answers))
        y_soft = correct_count / m
        y_hard = 1.0 if y_soft > 0.0 else 0.0
        return (y_soft, y_hard)


class OutcomeRewardEvaluator:
    """Outcome Reward Model scoring only the final state against ground truth."""

    @staticmethod
    def evaluate(final_answer: Any, ground_truth: Any) -> float:
        return 1.0 if final_answer == ground_truth else 0.0


def run_orm_vs_prm_benchmark() -> Dict[str, Any]:
    """
    Demonstrates the ORM False-Positive Failure Mode:
    A student derivation reaches the correct answer (+10),
    but contains two internal sign-flip errors that cancel out.
    """
    # Problem: Solve 3x - 5 = 25  => 3x = 30 => x = 10
    # Flawed derivation:
    # Step 1: 3x - 5 = 25 => 3x = 25 - 5 = 20  [Error: subtracted 5 instead of adding]
    # Step 2: 3x = 20     => x = 20 - 10 = 10  [Error: subtracted 10 instead of dividing by 3]
    flawed_steps = [
        "3x - 5 = 25 => 3x = 25 - 5 = 20",
        "3x = 20 => x = 20 - 10 = 10"
    ]
    step_scores = [0.05, 0.05]
    final_ans = 10
    target_ans = 10

    orm_score = OutcomeRewardEvaluator.evaluate(final_ans, target_ans)
    prm = ProcessRewardEvaluator()
    prm_metrics = prm.evaluate_trajectory(step_scores)

    return {
        "flawed_steps": flawed_steps,
        "final_answer": final_ans,
        "ground_truth": target_ans,
        "orm_score": orm_score,
        "prm_min": prm_metrics["min"],
        "prm_prod": prm_metrics["prod"],
        "prm_geom_mean": prm_metrics["geometric_mean"],
    }


if __name__ == "__main__":
    print("[Winograd - Data Specialist] PRM Evaluator & Benchmark Test:")
    prm = ProcessRewardEvaluator()
    sample_scores = [0.95, 0.90, 0.85, 0.40]
    metrics = prm.evaluate_trajectory(sample_scores)
    print(f"Sample Step Scores: {sample_scores}")
    print(f"PRM Min: {metrics['min']:.4f}, Prod: {metrics['prod']:.4f}, Geom: {metrics['geometric_mean']:.4f}")

    bench = run_orm_vs_prm_benchmark()
    print(f"\nORM vs PRM Benchmark:")
    print(f"  ORM Score: {bench['orm_score']} (False Positive Trap!)")
    print(f"  PRM Min:   {bench['prm_min']} (Defect Caught!)")
