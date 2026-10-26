"""
USSE Noosphere — Bridge Astrogation & Transformer Attention Core
Mission 03, Part 3: Grouped-Query Attention (GQA) & KV-Cache Benchmarking

Squadron: Squadron Winograd
Station Officer: Hassaan Ahmad Khawaja (Data & Payload Specialist)
Collaborating Officers:
  - Muhammad Qasim Siddiqui (Systems Architect)
  - Muhammad Usman Maratib (Communications & Protocol Officer)
  - Muhammad Qasim Siddiqui (Security & Ethics Sentinel)

Waypoint: Pleiades Open Cluster (SEC-03-M45, 444 ly from Sol — Seven Sisters)
"""

import time
import math
import torch
import torch.nn as nn
from typing import Optional, Tuple, Dict, Any, List


class KVCache:
    """
    Flexible Key-Value Cache buffer for autoregressive token decoding.
    Supports both dynamic concatenation and preallocated buffer updates.
    """

    def __init__(
        self,
        max_batch_size: Optional[int] = None,
        max_seq_len: Optional[int] = None,
        n_kv_heads: Optional[int] = None,
        head_dim: Optional[int] = None,
        device: str = "cpu"
    ):
        self.dynamic = max_batch_size is None or max_seq_len is None
        if not self.dynamic:
            self.k_cache = torch.zeros(max_batch_size, n_kv_heads, max_seq_len, head_dim, device=device)
            self.v_cache = torch.zeros(max_batch_size, n_kv_heads, max_seq_len, head_dim, device=device)
            self.seq_len = 0
        else:
            self.k: Optional[torch.Tensor] = None
            self.v: Optional[torch.Tensor] = None

    def update(
        self,
        k_val: torch.Tensor,
        v_val: torch.Tensor,
        start_pos: Optional[int] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Updates cache with newly computed key and value slices.
        """
        if not self.dynamic and start_pos is not None:
            b, h, seq_len, d = k_val.shape
            self.k_cache[:b, :h, start_pos : start_pos + seq_len, :d] = k_val
            self.v_cache[:b, :h, start_pos : start_pos + seq_len, :d] = v_val
            self.seq_len = start_pos + seq_len
            return self.k_cache[:b, :h, : self.seq_len, :d], self.v_cache[:b, :h, : self.seq_len, :d]
        else:
            if self.k is None or self.v is None:
                self.k = k_val
                self.v = v_val
            else:
                self.k = torch.cat([self.k, k_val], dim=-2)
                self.v = torch.cat([self.v, v_val], dim=-2)
            return self.k, self.v

    def reset(self) -> None:
        if self.dynamic:
            self.k = None
            self.v = None
        else:
            self.seq_len = 0

    def get_memory_mb(self) -> float:
        """Returns memory occupied by cache in Megabytes."""
        if not self.dynamic:
            bytes_total = self.k_cache.element_size() * (self.k_cache.nelement() + self.v_cache.nelement())
        else:
            if self.k is None or self.v is None:
                return 0.0
            bytes_total = self.k.element_size() * (self.k.nelement() + self.v.nelement())
        return bytes_total / (1024 * 1024)


class GQAAttention(nn.Module):
    """
    Grouped-Query Attention (GQA) Layer:
      - H_q: Number of query heads (e.g. 32)
      - H_kv: Number of key-value heads (e.g. 8)
      - Repeat factor: num_queries_per_kv = H_q // H_kv (e.g. 4)
      - Key/Value tensors expanded via repeat_interleave to match query heads.
    """

    def __init__(
        self,
        d_model: int = 1024,
        num_query_heads: Optional[int] = None,
        num_kv_heads: Optional[int] = None,
        num_q_heads: Optional[int] = None,
        n_kv_heads: Optional[int] = None,
        head_dim: Optional[int] = None
    ):
        super().__init__()
        h_q = num_query_heads if num_query_heads is not None else (num_q_heads if num_q_heads is not None else 16)
        h_kv = num_kv_heads if num_kv_heads is not None else (n_kv_heads if n_kv_heads is not None else 4)

        assert h_q % h_kv == 0, f"num_query_heads ({h_q}) must be divisible by num_kv_heads ({h_kv})"

        self.d_model = d_model
        self.num_query_heads = h_q
        self.num_kv_heads = h_kv
        self.num_queries_per_kv = h_q // h_kv
        self.head_dim = head_dim if head_dim is not None else d_model // h_q

        # Projections
        self.w_q = nn.Linear(d_model, h_q * self.head_dim, bias=False)
        self.w_k = nn.Linear(d_model, h_kv * self.head_dim, bias=False)
        self.w_v = nn.Linear(d_model, h_kv * self.head_dim, bias=False)
        self.w_o = nn.Linear(h_q * self.head_dim, d_model, bias=False)

    def forward(
        self,
        x: torch.Tensor,
        kv_cache: Optional[KVCache] = None,
        start_pos: Optional[int] = None,
        is_causal: bool = True
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
          x: [batch, seq_len, d_model]
          kv_cache: Optional stateful KVCache buffer
        """
        batch_size, seq_len, _ = x.shape

        q = self.w_q(x).view(batch_size, seq_len, self.num_query_heads, self.head_dim).transpose(1, 2)
        k = self.w_k(x).view(batch_size, seq_len, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.w_v(x).view(batch_size, seq_len, self.num_kv_heads, self.head_dim).transpose(1, 2)

        if kv_cache is not None:
            k, v = kv_cache.update(k, v, start_pos=start_pos)

        # Broadcast KV heads to match Query heads
        k_expanded = k.repeat_interleave(self.num_queries_per_kv, dim=1)
        v_expanded = v.repeat_interleave(self.num_queries_per_kv, dim=1)

        scale = 1.0 / math.sqrt(self.head_dim)
        scores = torch.matmul(q, k_expanded.transpose(-2, -1)) * scale

        # Masking for autoregressive decoding
        total_k_len = k_expanded.size(-2)
        if is_causal and seq_len > 1:
            mask = torch.tril(torch.ones(seq_len, total_k_len, device=x.device, dtype=torch.bool))
            scores = scores.masked_fill(mask == 0, float("-inf"))

        attn_weights = torch.softmax(scores, dim=-1)
        context = torch.matmul(attn_weights, v_expanded)

        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, -1)
        output = self.w_o(context)
        return output, attn_weights


def benchmark_vram_and_bandwidth(
    sequence_lengths: List[int] = [1024, 4096, 16384, 32768],
    num_layers: int = 32,
    head_dim: int = 128,
    precision_bytes: int = 2
) -> List[Dict[str, Any]]:
    architectures = [
        {"name": "MHA (Multi-Head, 32:32)", "h_q": 32, "h_kv": 32},
        {"name": "GQA (Grouped-Query, 32:8)", "h_q": 32, "h_kv": 8},
        {"name": "MQA (Multi-Query, 32:1)",   "h_q": 32, "h_kv": 1}
    ]

    records = []
    tokens_per_sec = 50

    for N in sequence_lengths:
        for arch in architectures:
            h_kv = arch["h_kv"]
            bytes_total = 2 * num_layers * h_kv * head_dim * precision_bytes * N
            mb_total = bytes_total / (1024 ** 2)
            bw_gbps = (bytes_total * tokens_per_sec) / (1024 ** 3)

            records.append({
                "seq_len": N,
                "arch": arch["name"],
                "h_kv": h_kv,
                "vram_mb": round(mb_total, 2),
                "bandwidth_gbps": round(bw_gbps, 2)
            })
    return records


def measure_decoding_latency(
    arch_type: str = "GQA",
    seq_len: int = 512,
    num_decode_steps: int = 10
) -> float:
    d_model = 512
    h_q = 16
    h_kv = 4 if arch_type == "GQA" else (16 if arch_type == "MHA" else 1)

    layer = GQAAttention(d_model=d_model, num_query_heads=h_q, num_kv_heads=h_kv)
    cache = KVCache()

    prompt = torch.randn(1, seq_len, d_model)
    with torch.no_grad():
        _, _ = layer(prompt, kv_cache=cache, is_causal=True)

    new_token = torch.randn(1, 1, d_model)
    start_time = time.perf_counter()
    with torch.no_grad():
        for _ in range(num_decode_steps):
            _, _ = layer(new_token, kv_cache=cache, is_causal=False)
    elapsed = time.perf_counter() - start_time
    return (elapsed / num_decode_steps) * 1000.0


def main():
    print("=== SQUADRON WINOGRAD: GQA & KV-CACHE BENCHMARK ===")
    layer = GQAAttention(d_model=256, num_query_heads=8, num_kv_heads=2)
    cache = KVCache()
    x_prefill = torch.randn(1, 4, 256)
    out_prefill, _ = layer(x_prefill, kv_cache=cache)
    print(f"Prefill Output Shape: {out_prefill.shape}")

    x_step = torch.randn(1, 1, 256)
    out_step, _ = layer(x_step, kv_cache=cache)
    print(f"Decode Step Output:   {out_step.shape}")

    print("\n--- THEORETICAL VRAM & MEMORY BANDWIDTH BENCHMARK (32 Layers, FP16) ---")
    benchmark_data = benchmark_vram_and_bandwidth([1024, 4096, 16384, 32768])
    print(f"{'Seq Len':<10} | {'Architecture':<26} | {'VRAM Footprint':<16} | {'Bandwidth @ 50 tok/s'}")
    print("-" * 75)
    for row in benchmark_data:
        print(f"{row['seq_len']:<10} | {row['arch']:<26} | {row['vram_mb']:>8.2f} MB     | {row['bandwidth_gbps']:>6.2f} GB/s")

    latency_gqa = measure_decoding_latency("GQA", seq_len=256)
    latency_mha = measure_decoding_latency("MHA", seq_len=256)
    print(f"\nAverage Decoding Latency per token (CPU):")
    print(f"  MHA (16:16): {latency_mha:.2f} ms")
    print(f"  GQA (16:4):  {latency_gqa:.2f} ms")
    print("GQA and KV-Cache benchmarking verified and completed!\n")


if __name__ == "__main__":
    main()
