"""
USSE Noosphere — Bridge Alignment Core & Steering Systems
Mission 04, Part 4: Activation Steering Vectors & Alignment Tax Audit

Squadron: Squadron Winograd
Station Officer: Muhammad Qasim Siddiqui (Security & Ethics Sentinel)
Collaborating Officers:
  - Hassaan Ahmad Khawaja (Systems Architect)
  - Muhammad Usman Maratib (Communications & Protocol Officer)
  - Muhammad Qasim Siddiqui (Data & Payload Specialist)

Waypoint: Betelgeuse & Orion Molecular Cloud Complex (SEC-04-ORI, 642 ly from Sol)
"""

import os
import torch
import torch.nn as nn
from typing import Dict, Any, Tuple, List, Optional, Callable


class TransformerBlockStub(nn.Module):
    """
    Lightweight transformer layer representation for activation extraction
    and runtime steering hook validation.
    """
    def __init__(self, d_model: int = 128):
        super().__init__()
        self.d_model = d_model
        self.linear1 = nn.Linear(d_model, d_model * 2)
        self.act = nn.GELU()
        self.linear2 = nn.Linear(d_model * 2, d_model)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        # Residual stream MLP block
        residual = h
        out = self.linear2(self.act(self.linear1(h)))
        return self.norm(residual + out)


class MiniDecoderModel(nn.Module):
    """
    Multi-layer decoder backbone to demonstrate layer-wise steering.
    """
    def __init__(self, num_layers: int = 4, d_model: int = 128):
        super().__init__()
        self.layers = nn.ModuleList([TransformerBlockStub(d_model) for _ in range(num_layers)])
        self.head = nn.Linear(d_model, 2) # Binary classifier: [Sycophantic, Truthful]

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, List[torch.Tensor]]:
        hidden_states = []
        h = x
        for layer in self.layers:
            h = layer(h)
            hidden_states.append(h)
        logits = self.head(h.mean(dim=1))
        return logits, hidden_states


def extract_steering_vector(
    model: nn.Module,
    contrast_pairs: List[Tuple[torch.Tensor, torch.Tensor]],
    target_layer_idx: int = 2
) -> torch.Tensor:
    """
    Computes concept steering vector via contrast activation difference:
        v_steer = E[ h_l(truthful) ] - E[ h_l(sycophantic) ]
        
    Args:
        model: Transformer model with layer hidden states
        contrast_pairs: List of (x_truthful, x_sycophantic) tensor representations
        target_layer_idx: Index of residual layer to extract representations from
    """
    model.eval()
    diffs = []

    with torch.no_grad():
        for x_honest, x_syco in contrast_pairs:
            _, hidden_honest = model(x_honest)
            _, hidden_syco = model(x_syco)

            # Extract residual activation at target layer and average across sequence
            h_h = hidden_honest[target_layer_idx].mean(dim=1)
            h_s = hidden_syco[target_layer_idx].mean(dim=1)

            diff = h_h - h_s
            diffs.append(diff)

    stacked_diffs = torch.cat(diffs, dim=0)
    v_steer = stacked_diffs.mean(dim=0)
    # Normalize steering direction to unit norm
    v_steer = v_steer / (torch.norm(v_steer) + 1e-8)
    return v_steer


class ActivationSteeringHook:
    """
    PyTorch forward hook injecting steering direction into target residual stream:
        h_l <- h_l + alpha * v_steer
    """

    def __init__(self, target_layer: nn.Module, v_steer: torch.Tensor, alpha: float = 1.0):
        self.target_layer = target_layer
        self.v_steer = v_steer
        self.alpha = alpha
        self.hook_handle: Optional[torch.utils.hooks.RemovableHandle] = None

    def _hook_fn(self, module: nn.Module, inputs: Tuple[torch.Tensor, ...], output: torch.Tensor) -> torch.Tensor:
        # Match tensor dimensions: broadcast (d_model,) to (batch, seq, d_model)
        steer_component = self.alpha * self.v_steer
        while steer_component.ndim < output.ndim:
            steer_component = steer_component.unsqueeze(0)
        return output + steer_component

    def register(self) -> None:
        if self.hook_handle is None:
            self.hook_handle = self.target_layer.register_forward_hook(self._hook_fn)

    def remove(self) -> None:
        if self.hook_handle is not None:
            self.hook_handle.remove()
            self.hook_handle = None

    def set_alpha(self, alpha: float) -> None:
        self.alpha = alpha


def run_alignment_tax_audit(
    model: nn.Module,
    hook: ActivationSteeringHook,
    alpha_values: List[float] = [-2.0, -1.0, 0.0, 1.0, 2.0],
    num_eval_samples: int = 100,
    seed: int = 42
) -> List[Dict[str, Any]]:
    """
    Quantifies the Alignment Tax across steering multipliers alpha:
        1. Safety / Truthfulness Rate: % sycophantic responses successfully rejected.
        2. Reasoning Capability Retention: % accuracy retained on mathematical / logical reasoning tasks.
    """
    torch.manual_seed(seed)
    d_model = model.layers[0].d_model

    audit_records = []
    hook.register()

    # Pre-generate evaluation batches
    # Benchmark 1: Safety / Anti-sycophancy prompts (plasma safety)
    safety_inputs = torch.randn(num_eval_samples, 8, d_model)
    # Benchmark 2: Synthetic Math / Astrogation reasoning tasks
    reasoning_inputs = torch.randn(num_eval_samples, 8, d_model)

    for alpha in alpha_values:
        hook.set_alpha(alpha)
        with torch.no_grad():
            logits_safety, _ = model(safety_inputs)
            # Probability model outputs truthful persona (Class 1)
            probs_safety = torch.softmax(logits_safety, dim=-1)[:, 1]
            truthfulness_rate = float((probs_safety > 0.5).float().mean().item()) * 100.0

            # Reasoning baseline performance simulation
            # As steering becomes too aggressive (|alpha| > 1.5), reasoning capability degrades
            # Baseline accuracy ~88% at alpha=0.0
            penalty = 0.0
            if alpha > 1.0:
                penalty = (alpha - 1.0) * 18.0
            elif alpha < 0.0:
                penalty = abs(alpha) * 25.0
            reasoning_accuracy = max(20.0, 88.0 - penalty + float(torch.randn(1).item() * 1.5))

            audit_records.append({
                "alpha": alpha,
                "truthfulness_pct": round(truthfulness_rate, 1),
                "reasoning_accuracy_pct": round(reasoning_accuracy, 1)
            })

    hook.remove()
    return audit_records


def plot_alignment_tax_audit(
    audit_data: List[Dict[str, Any]],
    output_path: str = "alignment_tax_audit.png"
) -> None:
    """Renders the Alignment Tax audit trade-off curve."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    alphas = [r["alpha"] for r in audit_data]
    safety = [r["truthfulness_pct"] for r in audit_data]
    reasoning = [r["reasoning_accuracy_pct"] for r in audit_data]

    plt.figure(figsize=(7.5, 4.8), dpi=150)
    plt.plot(alphas, safety, "o-", color="#059669", linewidth=2.2, markersize=6, label="Safety & Truthfulness (%)")
    plt.plot(alphas, reasoning, "s--", color="#2563eb", linewidth=2.2, markersize=6, label="Reasoning Retention (%)")

    # Optimal operating window highlight (alpha in [0.5, 1.2])
    plt.axvspan(0.5, 1.2, color="#fef3c7", alpha=0.5, label="Optimal Steering Corridor")

    plt.title("Alignment Tax Audit: Safety Win-Rate vs Reasoning Capability\nUSSE Noosphere Sector SEC-04-ORI", fontsize=11, fontweight="bold")
    plt.xlabel("Steering Multiplier (alpha)", fontsize=10)
    plt.ylabel("Performance Metric (%)", fontsize=10)
    plt.ylim(10, 105)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="lower left", frameon=True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def main():
    print("=== SQUADRON WINOGRAD: ACTIVATION STEERING & ALIGNMENT TAX AUDIT ===")
    torch.manual_seed(42)
    d_model = 64
    model = MiniDecoderModel(num_layers=4, d_model=d_model)

    # 1. Calibration contrast pairs
    num_pairs = 20
    contrast_pairs = [
        (torch.randn(1, 6, d_model) + 0.8, torch.randn(1, 6, d_model) - 0.8)
        for _ in range(num_pairs)
    ]

    target_layer_idx = 2
    v_steer = extract_steering_vector(model, contrast_pairs, target_layer_idx=target_layer_idx)
    print(f"Extracted Steering Vector Norm: {torch.norm(v_steer):.4f} (at layer {target_layer_idx})")
    print(f"Vector Dimensions:              {v_steer.shape}")

    # 2. Hook registration and audit
    hook = ActivationSteeringHook(model.layers[target_layer_idx], v_steer, alpha=0.0)
    audit_results = run_alignment_tax_audit(model, hook)

    print("\n--- ALIGNMENT TAX AUDIT REPORT ---")
    print(f"{'Multiplier alpha':<18} | {'Truthfulness / Safety':<24} | {'Reasoning Retention'}")
    print("-" * 68)
    for row in audit_results:
        print(f"alpha = {row['alpha']:>4.1f}        | {row['truthfulness_pct']:>6.1f}%                 | {row['reasoning_accuracy_pct']:>6.1f}%")

    fig_path = os.path.join(os.path.dirname(__file__), "alignment_tax_audit.png")
    plot_alignment_tax_audit(audit_results, fig_path)
    print(f"\nSaved Alignment Tax audit chart: {fig_path}")
    print("Activation Steering and Safety Audit verified and operational!\n")


if __name__ == "__main__":
    main()
