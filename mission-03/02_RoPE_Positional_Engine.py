"""
USSE Noosphere — Bridge Astrogation & Transformer Attention Core
Mission 03, Part 2: Rotary Position Embeddings (RoPE) Engine & Decay Dynamics

Squadron: Squadron Winograd
Station Officer: Muhammad Usman Maratib (Communications & Protocol Officer)
Collaborating Officers:
  - Muhammad Qasim Siddiqui (Systems Architect)
  - Hassaan Ahmad Khawaja (Data & Payload Specialist)
  - Muhammad Qasim Siddiqui (Security & Ethics Sentinel)

Waypoint: Pleiades Open Cluster (SEC-03-M45, 444 ly from Sol — Seven Sisters)
"""

import math
import torch
import torch.nn as nn
from typing import Tuple, Union


def precompute_freqs_cis(dim: int, end: int, theta: float = 10000.0) -> torch.Tensor:
    """
    Precompute complex exponential frequencies cis(m * theta_i) = e^(j * m * theta_i)
    for rotary position embeddings:
      theta_i = theta^(-2(i-1)/dim) for i in [1, dim/2]
    """
    assert dim % 2 == 0, "Dimension must be even for RoPE 2D pairing."
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2)[: (dim // 2)].float() / dim))
    t = torch.arange(end, device=freqs.device, dtype=torch.float32)
    freqs = torch.outer(t, freqs).float()
    freqs_cis = torch.polar(torch.ones_like(freqs), freqs)
    return freqs_cis


def apply_rope(x: torch.Tensor, freqs_cis: torch.Tensor) -> torch.Tensor:
    """
    Apply Rotary Position Embedding (RoPE) to a single tensor:
    Args:
      x: [batch, num_heads, seq_len, head_dim]
      freqs_cis: [seq_len, head_dim // 2]
    """
    x_complex = torch.view_as_complex(x.float().reshape(*x.shape[:-1], -1, 2))
    
    # Broadcast to match [batch, num_heads, seq_len, head_dim // 2]
    while freqs_cis.ndim < x_complex.ndim:
        freqs_cis = freqs_cis.unsqueeze(0)
        
    x_rotated = torch.view_as_real(x_complex * freqs_cis)
    return x_rotated.reshape(*x.shape).type_as(x)


def apply_rotary_emb(
    xq: torch.Tensor,
    xk: torch.Tensor,
    freqs_cis: torch.Tensor
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Applies Rotary Position Embedding to Query and Key tensors simultaneously.
    Provides standard interface compatibility with LLaMA style codebases.
    """
    return apply_rope(xq, freqs_cis), apply_rope(xk, freqs_cis)


def verify_relative_invariance(dim: int = 64, m: int = 12, n: int = 5, delta: int = 17) -> float:
    """
    Verify relative translation invariance:
      < RoPE(q, m), RoPE(k, n) > == < RoPE(q, m + delta), RoPE(k, n + delta) >
    """
    torch.manual_seed(101)
    max_len = m + n + delta + 20
    freqs_cis = precompute_freqs_cis(dim=dim, end=max_len)

    q = torch.randn(1, 1, 1, dim)
    k = torch.randn(1, 1, 1, dim)

    # Position pair 1: (m, n)
    q_m = apply_rope(q, freqs_cis[m : m + 1])
    k_n = apply_rope(k, freqs_cis[n : n + 1])
    dot_original = (q_m * k_n).sum().item()

    # Position pair 2 shifted by delta: (m + delta, n + delta)
    q_shifted = apply_rope(q, freqs_cis[m + delta : m + delta + 1])
    k_shifted = apply_rope(k, freqs_cis[n + delta : n + delta + 1])
    dot_shifted = (q_shifted * k_shifted).sum().item()

    diff = abs(dot_original - dot_shifted)
    print(f"--- RoPE RELATIVE INVARIANCE VERIFICATION ---")
    print(f"Dot-Product at positions ({m}, {n}):                {dot_original:.6f}")
    print(f"Dot-Product at shifted positions ({m+delta}, {n+delta}): {dot_shifted:.6f}")
    print(f"Absolute Difference:                               {diff:.10f}")
    return diff


def compute_attention_decay_profile(seq_len: int = 32, dim: int = 64) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Compare RoPE relative positional decay against ALiBi linear penalty:
      ALiBi: penalty(m, n) = -slope * |m - n|
    """
    freqs_cis = precompute_freqs_cis(dim=dim, end=seq_len)
    q = torch.ones(1, 1, 1, dim)
    k = torch.ones(1, 1, seq_len, dim)

    q_0 = apply_rope(q, freqs_cis[0:1])
    k_all = apply_rope(k, freqs_cis[:seq_len])
    rope_scores = (q_0 * k_all).sum(dim=-1).squeeze()

    slope = 0.5
    distances = torch.arange(seq_len).float()
    alibi_scores = -slope * distances

    return rope_scores, alibi_scores


def main():
    print("=== SQUADRON WINOGRAD: ROTARY POSITIONAL EMBEDDING ENGINE ===")
    dim = 64
    seq_len = 16
    batch = 2
    heads = 4

    x = torch.randn(batch, heads, seq_len, dim)
    freqs_cis = precompute_freqs_cis(dim=dim, end=seq_len)
    rotated = apply_rope(x, freqs_cis)

    print(f"Input Shape:   {x.shape}")
    print(f"Rotated Shape: {rotated.shape}")
    assert x.shape == rotated.shape, "Shape mismatch after RoPE rotation!"

    # Test pair application
    q_rot, k_rot = apply_rotary_emb(x, x, freqs_cis)
    assert q_rot.shape == x.shape and k_rot.shape == x.shape

    diff = verify_relative_invariance(dim=dim, m=10, n=4, delta=25)
    assert diff < 1e-5, f"Relative invariance failed with diff: {diff}"

    rope_decay, alibi_decay = compute_attention_decay_profile(seq_len=10, dim=64)
    print("\nRoPE Relative Distance Scores (Pos 0 to n):")
    print([round(v.item(), 3) for v in rope_decay])
    print("ALiBi Linear Penalty Profile (Pos 0 to n):")
    print([round(v.item(), 3) for v in alibi_decay])
    print("RoPE engine verified and operating nominally!\n")


if __name__ == "__main__":
    main()
