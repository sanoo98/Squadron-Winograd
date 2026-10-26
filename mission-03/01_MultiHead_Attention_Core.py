"""
USSE Noosphere — Bridge Astrogation & Transformer Attention Core
Mission 03, Part 1: Scaled Dot-Product & Multi-Head Self-Attention from Scratch

Squadron: Squadron Winograd
Station Officer: Muhammad Qasim Siddiqui (Systems Architect)
Collaborating Officers:
  - Muhammad Usman Maratib (Communications & Protocol Officer)
  - Hassaan Ahmad Khawaja (Data & Payload Specialist)
  - Muhammad Qasim Siddiqui (Security & Ethics Sentinel)

Waypoint: Pleiades Open Cluster (SEC-03-M45, 444 ly from Sol — Seven Sisters)
"""

import math
import torch
import torch.nn as nn
from typing import Optional, Tuple


class ScaledDotProductAttention(nn.Module):
    """
    Scaled Dot-Product Attention:
      Attention(Q, K, V) = softmax( (Q * K^T) / sqrt(d_k) + M ) * V
    """

    def __init__(self, dropout: float = 0.0):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

    def forward(
        self,
        q: torch.Tensor,
        k: torch.Tensor,
        v: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
          q: [batch, num_heads, seq_len_q, head_dim]
          k: [batch, num_heads, seq_len_k, head_dim]
          v: [batch, num_heads, seq_len_k, head_dim]
          mask: Optional tensor broadcastable to [batch, num_heads, seq_len_q, seq_len_k]
        Returns:
          context: [batch, num_heads, seq_len_q, head_dim]
          attn_weights: [batch, num_heads, seq_len_q, seq_len_k]
        """
        d_k = q.size(-1)
        scale = 1.0 / math.sqrt(d_k)

        # Dot-product: [batch, heads, seq_len_q, seq_len_k]
        scores = torch.matmul(q, k.transpose(-2, -1)) * scale

        if mask is not None:
            scores = scores.masked_fill(mask == 0, float("-inf"))

        attn_weights = torch.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)

        context = torch.matmul(attn_weights, v)
        return context, attn_weights


class MultiHeadSelfAttention(nn.Module):
    """
    Multi-Head Self-Attention constructed from first principles:
      - Linear projections W_q, W_k, W_v in R^(d_model x d_model)
      - Output projection W_o in R^(d_model x d_model)
      - Multi-head splitting & lower-triangular causal masking
      - Supports both 'is_causal' and 'causal' keyword args for test compatibility
    """

    def __init__(self, d_model: int = 512, num_heads: int = 8, dropout: float = 0.0):
        super().__init__()
        assert d_model % num_heads == 0, f"d_model ({d_model}) must be divisible by num_heads ({num_heads})"

        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads

        # Linear projections from scratch
        self.w_q = nn.Linear(d_model, d_model, bias=False)
        self.w_k = nn.Linear(d_model, d_model, bias=False)
        self.w_v = nn.Linear(d_model, d_model, bias=False)
        self.w_o = nn.Linear(d_model, d_model, bias=False)

        self.attention = ScaledDotProductAttention(dropout=dropout)

    def forward(
        self,
        x: torch.Tensor,
        causal: bool = True,
        is_causal: Optional[bool] = None,
        attention_mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
          x: [batch_size, seq_len, d_model]
          causal / is_causal: Whether to apply lower-triangular causal masking
          attention_mask: Optional boolean or float mask of shape (batch_size, seq_len)
        Returns:
          output: [batch_size, seq_len, d_model]
          attn_weights: [batch_size, num_heads, seq_len, seq_len]
        """
        # Resolve causal flag
        use_causal = causal if is_causal is None else is_causal
        batch_size, seq_len, _ = x.shape

        # 1. Project inputs: [batch, seq_len, d_model]
        q = self.w_q(x)
        k = self.w_k(x)
        v = self.w_v(x)

        # 2. Reshape into parallel heads: (batch, num_heads, seq_len, head_dim)
        q = q.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = k.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = v.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)

        # 3. Construct causal and attention mask
        mask = None
        if use_causal:
            mask = torch.tril(torch.ones(seq_len, seq_len, device=x.device, dtype=torch.bool))
            mask = mask.view(1, 1, seq_len, seq_len)

        if attention_mask is not None:
            extra_mask = attention_mask.view(batch_size, 1, 1, seq_len).bool()
            mask = extra_mask if mask is None else (mask & extra_mask)

        # 4. Scaled Dot-Product Attention
        context, attn_weights = self.attention(q, k, v, mask=mask)

        # 5. Concatenate heads and project output: [batch, seq_len, d_model]
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)
        output = self.w_o(context)

        return output, attn_weights


def verify_variance_preservation(d_k: int = 64, num_samples: int = 100000) -> float:
    """
    Empirical unit test:
      If q_i, k_i ~ N(0, 1), then dot-product sum_{i=1}^{d_k} q_i * k_i has variance d_k.
      Scaling by 1 / sqrt(d_k) normalizes variance back to approximately 1.0.
    """
    torch.manual_seed(42)
    q = torch.randn(num_samples, d_k)
    k = torch.randn(num_samples, d_k)

    dot_products = (q * k).sum(dim=-1)
    scaled_dot_products = dot_products / math.sqrt(d_k)

    raw_var = dot_products.var().item()
    scaled_var = scaled_dot_products.var().item()

    print(f"--- VARIANCE PRESERVATION VALIDATION (d_k = {d_k}) ---")
    print(f"Unscaled Dot-Product Variance: {raw_var:.4f} (Theoretical ~ {d_k})")
    print(f"Scaled Dot-Product Variance:   {scaled_var:.4f} (Theoretical ~ 1.0000)")
    return scaled_var


def main():
    print("=== SQUADRON WINOGRAD: MULTI-HEAD SELF-ATTENTION VERIFICATION ===")
    d_model = 256
    num_heads = 4
    seq_len = 8
    batch_size = 2

    mha = MultiHeadSelfAttention(d_model=d_model, num_heads=num_heads)
    x = torch.randn(batch_size, seq_len, d_model)

    output, weights = mha(x, causal=True)
    print(f"Input Shape:         {x.shape}")
    print(f"Output Shape:        {output.shape}")
    print(f"Attn Weights Shape:  {weights.shape}")
    print(f"Causal Upper Check:  weights[0, 0, 0, 1].item() = {weights[0, 0, 0, 1].item():.4f} (Must be 0.0)")

    var_val = verify_variance_preservation(d_k=64)
    assert abs(var_val - 1.0) < 0.05, f"Variance {var_val} deviated too far from 1.0"
    print("Multi-Head Self-Attention core operational and verified!\n")


if __name__ == "__main__":
    main()
