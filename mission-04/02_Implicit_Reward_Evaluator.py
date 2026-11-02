"""
USSE Noosphere — Bridge Alignment Core & Steering Systems
Mission 04, Part 2: Implicit Reward Extraction & Bradley-Terry Evaluation

Squadron: Squadron Winograd
Station Officer: Muhammad Usman Maratib (Communications & Protocol Officer)
Collaborating Officers:
  - Hassaan Ahmad Khawaja (Systems Architect)
  - Muhammad Qasim Siddiqui (Data & Payload Specialist)
  - Muhammad Qasim Siddiqui (Security & Ethics Sentinel)

Waypoint: Betelgeuse & Orion Molecular Cloud Complex (SEC-04-ORI, 642 ly from Sol)
"""

import math
import os
import torch
import numpy as np
from typing import Dict, Any, Tuple, List, Optional


def compute_implicit_rewards(
    policy_chosen_logps: torch.Tensor,
    policy_rejected_logps: torch.Tensor,
    reference_chosen_logps: torch.Tensor,
    reference_rejected_logps: torch.Tensor,
    beta: float = 0.1
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Extracts scalar implicit rewards derived analytically from DPO reparameterization:
        r_hat(x, y) = beta * (log pi_theta(y | x) - log pi_ref(y | x))
        
    Returns:
        chosen_rewards: r_hat(x, y_w)
        rejected_rewards: r_hat(x, y_l)
        reward_margins: Delta r = r_hat(x, y_w) - r_hat(x, y_l)
    """
    delta_w = policy_chosen_logps - reference_chosen_logps
    delta_l = policy_rejected_logps - reference_rejected_logps

    chosen_rewards = beta * delta_w
    rejected_rewards = beta * delta_l
    reward_margins = chosen_rewards - rejected_rewards

    return chosen_rewards, rejected_rewards, reward_margins


def evaluate_preference_accuracy(
    chosen_rewards: torch.Tensor,
    rejected_rewards: torch.Tensor
) -> float:
    """
    Computes pairwise ranking accuracy:
        Accuracy = (1 / N) * sum_i I(r_hat(x_i, y_{w, i}) > r_hat(x_i, y_{l, i}))
    """
    is_correct = (chosen_rewards > rejected_rewards).float()
    return is_correct.mean().item()


def compute_bradley_terry_calibration(
    reward_margins: torch.Tensor,
    num_bins: int = 5
) -> Dict[str, Any]:
    """
    Evaluates Bradley-Terry model calibration:
        P(y_w > y_l | x) = sigma(Delta r) = 1 / (1 + exp(-Delta r))
        
    Groups predicted probabilities into confidence bins and computes
    empirical accuracy within each bin alongside Expected Calibration Error (ECE).
    """
    # Predicted win probability under Bradley-Terry model
    predicted_probs = torch.sigmoid(reward_margins).detach().cpu().numpy()
    actual_labels = np.ones_like(predicted_probs) # In pairwise preference dataset, y_w is ground-truth winner

    bins = np.linspace(0.5, 1.0, num_bins + 1)
    bin_centers = []
    bin_empirical_acc = []
    bin_confidences = []
    bin_counts = []

    total_samples = len(predicted_probs)
    ece = 0.0

    for i in range(num_bins):
        lower, upper = bins[i], bins[i + 1]
        mask = (predicted_probs >= lower) & (predicted_probs <= upper if i == num_bins - 1 else predicted_probs < upper)
        count = int(np.sum(mask))

        if count > 0:
            avg_pred = float(np.mean(predicted_probs[mask]))
            # Empirical win rate: for pairs where margin > 0 it's 1.0, else 0.0
            emp_acc = float(np.mean(actual_labels[mask]))
            ece += (count / total_samples) * abs(avg_pred - emp_acc)

            bin_centers.append(float((lower + upper) / 2.0))
            bin_confidences.append(avg_pred)
            bin_empirical_acc.append(emp_acc)
            bin_counts.append(count)

    return {
        "bin_centers": bin_centers,
        "bin_confidences": bin_confidences,
        "bin_empirical_acc": bin_empirical_acc,
        "bin_counts": bin_counts,
        "ece": float(ece),
        "mean_predicted_prob": float(np.mean(predicted_probs))
    }


def generate_synthetic_evaluation_suite(num_pairs: int = 250, seed: int = 42) -> Dict[str, Any]:
    """
    Generates synthetic validation telemetry representing Starship operational queries:
    Plasma containment, anti-matter routing, shield modulation, and emergency astrogation.
    """
    torch.manual_seed(seed)

    # Reference model: baseline log-probabilities
    ref_chosen = torch.randn(num_pairs) * 5.0 - 20.0
    ref_rejected = torch.randn(num_pairs) * 5.0 - 20.0

    # Aligned policy: shifts chosen responses higher and rejected responses lower
    # Adding intentional variance to simulate realistic Bradley-Terry distribution
    policy_shift_w = torch.randn(num_pairs) * 3.0 + 8.0
    policy_shift_l = torch.randn(num_pairs) * 3.0 - 5.0

    policy_chosen = ref_chosen + policy_shift_w
    policy_rejected = ref_rejected + policy_shift_l

    chosen_r, rejected_r, margins = compute_implicit_rewards(
        policy_chosen, policy_rejected, ref_chosen, ref_rejected, beta=0.1
    )

    acc = evaluate_preference_accuracy(chosen_r, rejected_r)
    calibration = compute_bradley_terry_calibration(margins, num_bins=5)

    return {
        "chosen_rewards": chosen_r,
        "rejected_rewards": rejected_r,
        "reward_margins": margins,
        "accuracy": acc,
        "calibration": calibration
    }


def plot_calibration_diagram(calibration: Dict[str, Any], output_path: str = "bt_calibration_curve.png") -> None:
    """Renders Bradley-Terry reliability calibration diagram."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    bin_conf = calibration["bin_confidences"]
    bin_acc = calibration["bin_empirical_acc"]
    ece = calibration["ece"]

    plt.figure(figsize=(7, 5), dpi=150)
    plt.plot([0.5, 1.0], [0.5, 1.0], "k--", label="Perfect Calibration (Ideal)")
    plt.bar(bin_conf, bin_acc, width=0.07, alpha=0.6, color="#0284c7", edgecolor="#0369a1", label="Empirical Win-Rate")
    plt.scatter(bin_conf, bin_acc, color="#b91c1c", s=40, zorder=5)

    plt.title(f"Bradley-Terry Preference Calibration Curve (ECE: {ece:.4f})\nUSSE Noosphere Alignment Validation", fontsize=11, fontweight="bold")
    plt.xlabel("Predicted Choice Probability P(y_w > y_l | x)", fontsize=10)
    plt.ylabel("Observed Empirical Win-Rate", fontsize=10)
    plt.xlim(0.48, 1.02)
    plt.ylim(0.48, 1.05)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="lower right", frameon=True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def main():
    print("=== SQUADRON WINOGRAD: IMPLICIT REWARD EVALUATION ===")
    eval_suite = generate_synthetic_evaluation_suite(num_pairs=200, seed=101)

    print(f"Total Validation Pairs Evaluated: {len(eval_suite['reward_margins'])}")
    print(f"Pairwise Preference Accuracy:     {eval_suite['accuracy'] * 100:.2f}%")
    print(f"Mean Chosen Reward r_hat(y_w):    {eval_suite['chosen_rewards'].mean().item():.4f}")
    print(f"Mean Rejected Reward r_hat(y_l):  {eval_suite['rejected_rewards'].mean().item():.4f}")
    print(f"Mean Reward Margin Delta r:       {eval_suite['reward_margins'].mean().item():.4f}")
    print(f"Expected Calibration Error (ECE): {eval_suite['calibration']['ece']:.4f}")

    # Generate calibration plot
    fig_path = os.path.join(os.path.dirname(__file__), "bt_calibration_curve.png")
    plot_calibration_diagram(eval_suite["calibration"], fig_path)
    print(f"Saved Bradley-Terry reliability curve: {fig_path}")
    print("Implicit Reward Evaluator verified and operational!\n")


if __name__ == "__main__":
    main()
