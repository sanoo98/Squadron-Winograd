"""
Squadron Winograd Unit Tests for Mission 03:
  - Multi-Head Self-Attention from Scratch
  - Rotary Positional Embeddings (RoPE) Invariance
  - Grouped-Query Attention (GQA) & KV-Cache Stateful Decoding

Station Officer: Muhammad Qasim Siddiqui (Systems Architect)
"""

import pytest
import math
import torch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from importlib import import_module
mha_module = import_module("01_MultiHead_Attention_Core")
rope_module = import_module("02_RoPE_Positional_Engine")
gqa_module = import_module("03_GQA_and_KVCache_Benchmark")

MultiHeadSelfAttention = mha_module.MultiHeadSelfAttention
verify_variance = mha_module.verify_variance_preservation

apply_rope = rope_module.apply_rope
precompute_freqs_cis = rope_module.precompute_freqs_cis
verify_rope_invariance = rope_module.verify_relative_invariance

GQAAttention = gqa_module.GQAAttention
KVCache = gqa_module.KVCache


def test_mha_tensor_shapes():
    """Verify input-to-output shape preservation and attention weights shape."""
    batch_size = 2
    seq_len = 8
    d_model = 128
    num_heads = 4

    mha = MultiHeadSelfAttention(d_model=d_model, num_heads=num_heads)
    x = torch.randn(batch_size, seq_len, d_model)
    out, weights = mha(x, is_causal=True)

    assert out.shape == (batch_size, seq_len, d_model)
    assert weights.shape == (batch_size, num_heads, seq_len, seq_len)


def test_mha_causal_masking():
    """Verify upper-triangular elements in attention weights are strictly zero."""
    mha = MultiHeadSelfAttention(d_model=64, num_heads=2)
    x = torch.randn(1, 6, 64)
    _, weights = mha(x, is_causal=True)

    # Upper triangular above diagonal should be 0.0
    for i in range(6):
        for j in range(i + 1, 6):
            assert weights[0, 0, i, j].item() == 0.0, f"Causal leak detected at position ({i}, {j})"


def test_mha_variance_preservation():
    """Verify dot-product variance scales to ~1.0."""
    scaled_var = verify_variance(d_k=64, num_samples=50000)
    assert abs(scaled_var - 1.0) < 0.08, f"Variance {scaled_var} deviated from 1.0"


def test_rope_tensor_shape_preservation():
    """Verify RoPE retains identical tensor dimensions after rotation."""
    dim = 32
    seq_len = 10
    x = torch.randn(2, 4, seq_len, dim)
    freqs = precompute_freqs_cis(dim=dim, end=seq_len)
    x_rot = apply_rope(x, freqs)
    assert x_rot.shape == x.shape


def test_rope_relative_translation_invariance():
    """Verify <RoPE(q, m), RoPE(k, n)> == <RoPE(q, m+d), RoPE(k, n+d)>."""
    diff = verify_rope_invariance(dim=64, m=8, n=3, delta=15)
    assert diff < 1e-5, f"RoPE relative invariance failure with diff {diff}"


def test_gqa_kv_cache_stateful_decoding():
    """Verify KV-Cache accumulates tokens during sequential decoding."""
    d_model = 128
    h_q = 8
    h_kv = 2
    head_dim = d_model // h_q

    layer = GQAAttention(d_model=d_model, num_query_heads=h_q, num_kv_heads=h_kv)
    cache = KVCache()

    # Step 1: Prefill 4 tokens
    x_prompt = torch.randn(1, 4, d_model)
    out_prefill, _ = layer(x_prompt, kv_cache=cache)
    assert out_prefill.shape == (1, 4, d_model)
    assert cache.k.shape == (1, h_kv, 4, head_dim)

    # Step 2: Decode 1 token
    x_next = torch.randn(1, 1, d_model)
    out_next, _ = layer(x_next, kv_cache=cache)
    assert out_next.shape == (1, 1, d_model)
    assert cache.k.shape == (1, h_kv, 5, head_dim)
    assert cache.v.shape == (1, h_kv, 5, head_dim)
