"""
USSE Noosphere — Bridge Alignment Core & Steering Systems
Mission 04, Part 1: PyTorch DPO Loss Core & Log-Likelihood Extraction

Squadron: Squadron Winograd
Station Officer: Hassaan Ahmad Khawaja (Systems Architect)
Collaborating Officers:
  - Muhammad Usman Maratib (Communications & Protocol Officer)
  - Muhammad Qasim Siddiqui (Data & Payload Specialist)
  - Muhammad Qasim Siddiqui (Security & Ethics Sentinel)

Waypoint: Betelgeuse & Orion Molecular Cloud Complex (SEC-04-ORI, 642 ly from Sol)
Subsystem Repair: Subsystem 04: Plasma Ignition & Ethical Steering Core (+7.1% -> 28.4% total)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Dict, Any, Optional


def get_batch_logps(
    logits: torch.Tensor,
    labels: torch.Tensor,
    average_log_prob: bool = False,
    label_pad_token_id: int = -100
) -> torch.Tensor:
    """
    Vectorized extraction of sequence log-probabilities via gather operations.
    Computes:
        log P(y | x) = sum_{t} log P(y_t | x, y_{<t})
    
    Args:
        logits: Tensor of shape (batch_size, seq_len, vocab_size)
        labels: Tensor of shape (batch_size, seq_len) with target token indices
        average_log_prob: If True, normalizes sum by sequence token count
        label_pad_token_id: Masked pad token index (default: -100)
        
    Returns:
        Tensor of shape (batch_size,) containing per-sequence log probabilities
    """
    assert logits.shape[:-1] == labels.shape, (
        f"Logits shape {logits.shape[:-1]} must match labels shape {labels.shape}"
    )

    # 1. Compute log-softmax across vocabulary: (batch_size, seq_len, vocab_size)
    log_probs = F.log_softmax(logits, dim=-1)

    # 2. Construct binary mask excluding padding/masked tokens
    loss_mask = labels != label_pad_token_id

    # 3. Clamp labels for gather index safety (replace -100 with 0 temporarily)
    safe_labels = labels.masked_fill(~loss_mask, 0)

    # 4. Gather log-probabilities corresponding to ground-truth token indices
    per_token_logps = torch.gather(
        log_probs,
        dim=-1,
        index=safe_labels.unsqueeze(-1)
    ).squeeze(-1)

    # 5. Mask out padding contributions
    per_token_logps = per_token_logps * loss_mask

    # 6. Sum across time dimension
    seq_logps = per_token_logps.sum(dim=-1)

    if average_log_prob:
        token_counts = loss_mask.sum(dim=-1).float().clamp(min=1.0)
        seq_logps = seq_logps / token_counts

    return seq_logps


class DPOLoss(nn.Module):
    """
    Direct Preference Optimization (DPO) Loss Module:
        L_DPO(theta; pi_ref) = -E_{(x, y_w, y_l)} [ log sigma( beta * (Delta_w - Delta_l) ) ]
    where:
        Delta_w = log pi_theta(y_w | x) - log pi_ref(y_w | x)
        Delta_l = log pi_theta(y_l | x) - log pi_ref(y_l | x)
    """

    def __init__(
        self,
        beta: float = 0.1,
        label_smoothing: float = 0.0,
        reference_free: bool = False
    ):
        super().__init__()
        self.beta = beta
        self.label_smoothing = label_smoothing
        self.reference_free = reference_free

    def forward(
        self,
        policy_chosen_logps: torch.Tensor,
        policy_rejected_logps: torch.Tensor,
        reference_chosen_logps: Optional[torch.Tensor] = None,
        reference_rejected_logps: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Computes DPO loss, chosen rewards, and rejected rewards.
        
        Args:
            policy_chosen_logps: log pi_theta(y_w | x), shape (batch,)
            policy_rejected_logps: log pi_theta(y_l | x), shape (batch,)
            reference_chosen_logps: log pi_ref(y_w | x), shape (batch,)
            reference_rejected_logps: log pi_ref(y_l | x), shape (batch,)
            
        Returns:
            Tuple of:
                loss: scalar DPO loss tensor
                chosen_rewards: beta * Delta_w, shape (batch,)
                rejected_rewards: beta * Delta_l, shape (batch,)
        """
        if self.reference_free or reference_chosen_logps is None:
            reference_chosen_logps = torch.zeros_like(policy_chosen_logps)
            reference_rejected_logps = torch.zeros_like(policy_rejected_logps)

        # Compute log-ratios relative to reference policy
        delta_w = policy_chosen_logps - reference_chosen_logps
        delta_l = policy_rejected_logps - reference_rejected_logps

        logits = self.beta * (delta_w - delta_l)

        # Numerically stable loss computation using logsigmoid
        if self.label_smoothing == 0.0:
            losses = -F.logsigmoid(logits)
        else:
            # Generalized cross-entropy with label smoothing
            losses = (
                -F.logsigmoid(logits) * (1.0 - self.label_smoothing)
                - F.logsigmoid(-logits) * self.label_smoothing
            )

        loss = losses.mean()

        # Implicit reward metrics
        chosen_rewards = (self.beta * delta_w).detach()
        rejected_rewards = (self.beta * delta_l).detach()

        return loss, chosen_rewards, rejected_rewards


def verify_gradient_isolation() -> Dict[str, Any]:
    """
    Validates that backpropagating through DPOLoss computes gradients strictly
    for active policy parameters while leaving reference model parameters frozen.
    """
    torch.manual_seed(42)
    vocab_size = 64
    d_model = 32
    seq_len = 6
    batch_size = 2

    # Simple 1-layer policy and reference models
    policy_head = nn.Linear(d_model, vocab_size, bias=False)
    reference_head = nn.Linear(d_model, vocab_size, bias=False)

    # Copy weights initially
    reference_head.load_state_dict(policy_head.state_dict())
    reference_head.eval()
    for param in reference_head.parameters():
        param.requires_grad = False

    # Synthetic input representations and token labels
    hidden_chosen = torch.randn(batch_size, seq_len, d_model)
    hidden_rejected = torch.randn(batch_size, seq_len, d_model)

    labels_w = torch.randint(0, vocab_size, (batch_size, seq_len))
    labels_l = torch.randint(0, vocab_size, (batch_size, seq_len))

    # Mask out last token as padding
    labels_w[:, -1] = -100
    labels_l[:, -1] = -100

    # Policy logits
    pi_logits_w = policy_head(hidden_chosen)
    pi_logits_l = policy_head(hidden_rejected)

    # Reference logits (detached / no_grad)
    with torch.no_grad():
        ref_logits_w = reference_head(hidden_chosen)
        ref_logits_l = reference_head(hidden_rejected)

    # Extract logps
    pi_logps_w = get_batch_logps(pi_logits_w, labels_w)
    pi_logps_l = get_batch_logps(pi_logits_l, labels_l)
    ref_logps_w = get_batch_logps(ref_logits_w, labels_w)
    ref_logps_l = get_batch_logps(ref_logits_l, labels_l)

    dpo = DPOLoss(beta=0.1)
    loss, r_w, r_l = dpo(pi_logps_w, pi_logps_l, ref_logps_w, ref_logps_l)

    # Backward pass
    policy_head.zero_grad()
    loss.backward()

    policy_has_grad = policy_head.weight.grad is not None and torch.norm(policy_head.weight.grad) > 0
    ref_grad_is_none = reference_head.weight.grad is None

    return {
        "loss": loss.item(),
        "reward_margin": (r_w - r_l).mean().item(),
        "policy_has_grad": policy_has_grad,
        "ref_grad_is_none": ref_grad_is_none
    }


def main():
    print("=== SQUADRON WINOGRAD: DPO LOSS CORE VERIFICATION ===")
    results = verify_gradient_isolation()
    print(f"Computed DPO Loss:           {results['loss']:.5f}")
    print(f"Mean Implicit Reward Margin: {results['reward_margin']:.5f}")
    print(f"Policy Parameters Received Gradients: {results['policy_has_grad']}")
    print(f"Reference Parameters Remain Frozen:   {results['ref_grad_is_none']}")
    assert results['policy_has_grad'], "Policy parameters failed to receive gradients!"
    assert results['ref_grad_is_none'], "Reference parameters leaked gradients!"
    print("DPO Loss Core operational, stable, and mathematically verified!\n")


if __name__ == "__main__":
    main()
