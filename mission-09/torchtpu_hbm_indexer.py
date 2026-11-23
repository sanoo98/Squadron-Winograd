"""
Mission 09: Part 3 - Data & Payload Specialist
Module: torchtpu_hbm_indexer.py
Cadet: Muhammad Qasim Siddiqui (Data & Payload Specialist)
Squadron: Winograd
Sector: SEC-09-LMC (Large Magellanic Cloud - Tarantula Nebula & SN 1987A)

Description:
    TorchTPU In-HBM ColBERT MaxSim Indexer & Epistemic Contradiction Resolver.
    Performs vectorized late-interaction token scoring and reconciles the
    Sanduleak -69 202 vs. Supernova 1987A temporal knowledge paradox.
"""

from __future__ import annotations
import math
from typing import List, Dict, Any, Optional
import torch


class TorchTPUHBMIndexer:
    """In-HBM Token Indexer computing late-interaction ColBERT MaxSim scores."""

    def __init__(self, device: Optional[torch.device] = None) -> None:
        if device is None:
            from adaptive_rag_tpu_router import get_compute_device
            self.device = get_compute_device()
        else:
            self.device = device

        if self.device.type in ["tpu", "cuda"]:
            self.dtype = torch.bfloat16
        else:
            self.dtype = torch.float32

    def compute_maxsim(
        self,
        Q: torch.Tensor,
        D: torch.Tensor,
        q_mask: Optional[torch.Tensor] = None,
        d_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Computes ColBERT MaxSim score via batched einsum:
            MaxSim(Q, D) = sum_{i=1}^{|Q|} max_{j=1}^{|D|} (E_Q,i . E_D,j^T)
        """
        if Q.dim() == 2:
            Q = Q.unsqueeze(0)  # [1, q_len, dim]

        # einsum: bqd, mjd -> bmqj
        sim_matrix = torch.einsum("bqd,mjd->bmqj", Q, D)

        if d_mask is not None:
            mask = d_mask.unsqueeze(0).unsqueeze(2)
            sim_matrix = sim_matrix.masked_fill(~mask, -1e4)

        max_per_query_token, _ = torch.max(sim_matrix, dim=-1)

        if q_mask is not None:
            q_m = q_mask.unsqueeze(1)
            max_per_query_token = max_per_query_token.masked_fill(~q_m, 0.0)

        scores = torch.sum(max_per_query_token, dim=-1)

        if scores.size(0) == 1:
            return scores.squeeze(0)
        return scores


class EpistemicContradictionResolver:
    """
    Reconciles conflicting temporal claims using authority and exponential decay:
        W(c) = alpha_auth * Authority(c) + (1 - alpha_auth) * exp(-lambda * (T_curr - T_pub))
    """

    def __init__(
        self,
        alpha_auth: float = 0.50,
        decay_lambda: float = 0.05,
        current_year: float = 2026.0,
    ) -> None:
        self.alpha_auth = alpha_auth
        self.decay_lambda = decay_lambda
        self.current_year = current_year

    def compute_weight(self, authority: float, year_published: float) -> float:
        delta_t = max(0.0, self.current_year - year_published)
        freshness = math.exp(-self.decay_lambda * delta_t)
        return (self.alpha_auth * authority) + ((1.0 - self.alpha_auth) * freshness)

    def resolve_contradiction(
        self,
        claim_a: Dict[str, Any],
        claim_b: Dict[str, Any],
    ) -> Dict[str, Any]:
        w_a = self.compute_weight(claim_a["authority"], claim_a["year"])
        w_b = self.compute_weight(claim_b["authority"], claim_b["year"])

        if w_a >= w_b:
            winner, loser = claim_a, claim_b
            win_score, lose_score = w_a, w_b
        else:
            winner, loser = claim_b, claim_a
            win_score, lose_score = w_b, w_a

        return {
            "winner_claim": winner["claim"],
            "winner_weight": win_score,
            "loser_claim": loser["claim"],
            "loser_weight": lose_score,
            "superseded": loser["source"],
            "rationale": f"Temporal authority weighting supersedes {loser['source']} ({loser['year']}) with {winner['source']} ({winner['year']}).",
        }


if __name__ == "__main__":
    print("[Winograd - Data Specialist] Standalone Indexer & Contradiction Test:")
    indexer = TorchTPUHBMIndexer()
    print(f"Device: {indexer.device}, Numeric Dtype: {indexer.dtype}")

    torch.manual_seed(42)
    Q = torch.randn(2, 4, device=indexer.device, dtype=indexer.dtype)
    Q = Q / torch.norm(Q, dim=-1, keepdim=True)
    D = torch.randn(2, 3, 4, device=indexer.device, dtype=indexer.dtype)
    D = D / torch.norm(D, dim=-1, keepdim=True)

    scores = indexer.compute_maxsim(Q, D)
    print(f"MaxSim Scores across 2 documents: {scores.tolist()}")

    resolver = EpistemicContradictionResolver()
    old_c = {"claim": "Sanduleak -69 202 is intact.", "authority": 0.80, "year": 1969.0, "source": "Old Catalog"}
    new_c = {"claim": "Sanduleak -69 202 exploded as SN 1987A.", "authority": 0.95, "year": 2024.0, "source": "New Survey"}
    res = resolver.resolve_contradiction(old_c, new_c)
    print(f"Active Truth: {res['winner_claim']} ({res['winner_weight']:.4f} vs {res['loser_weight']:.4f})")
