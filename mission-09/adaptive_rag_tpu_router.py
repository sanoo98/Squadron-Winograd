"""
Mission 09: Part 1 - Systems Architect
Module: adaptive_rag_tpu_router.py
Cadet: Hassaan Ahmad Khawaja (Systems Architect)
Squadron: Winograd
Sector: SEC-09-LMC (Large Magellanic Cloud - Tarantula Nebula & SN 1987A)

Description:
    Adaptive RAG Complexity Router & TorchTPU Device Dispatcher:
    Tri-regime routing across Route A (Parametric), Route B (Single-Step RAG), and Route C (Multi-Hop Loop)
    with automatic torch_tpu -> cuda -> cpu hardware probing.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple
import torch


def get_compute_device() -> torch.device:
    """Probes open-source torch_tpu, then falls back to cuda or cpu."""
    try:
        import torch_tpu
        if hasattr(torch, "device") and "tpu" in str(torch_tpu):
            return torch.device("tpu")
    except Exception:
        pass

    if torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


class AdaptiveRAGRouter:
    """
    Evaluates semantic query complexity and routes to optimal retrieval/parametric compute regime:
    Route A: No-Retrieval Parametric (score < tau_param)
    Route B: Single-Step Local HBM RAG (tau_param <= score < tau_agent)
    Route C: Multi-Hop Agentic Loop (score >= tau_agent)
    """

    PARAMETRIC_PATTERNS = [
        "speed of light", "planck constant", "gravitational constant", "definition",
        "pi value", "what is sol", "absolute zero"
    ]

    MULTIHOP_CONNECTIVES = [
        "compare", "relationship between", "how did", "correlate", "after which",
        "and then", "cross-reference", "versus"
    ]

    def __init__(self, tau_param: float = 0.35, tau_agent: float = 0.70) -> None:
        self.tau_param = tau_param
        self.tau_agent = tau_agent
        self.device = get_compute_device()

    def assess_complexity(self, query: str) -> float:
        """Computes query semantic complexity score in [0.0, 1.0]."""
        q_clean = query.lower().strip()

        for pat in self.PARAMETRIC_PATTERNS:
            if pat in q_clean and len(q_clean.split()) < 9:
                return 0.15

        score = 0.30

        # Multi-hop connective terms
        connectives = sum(1 for c in self.MULTIHOP_CONNECTIVES if c in q_clean)
        score += connectives * 0.25

        words = q_clean.split()
        if len(words) > 12:
            score += 0.20
        elif len(words) > 7:
            score += 0.10

        return min(1.0, max(0.0, score))

    def route_query(self, query: str) -> Dict[str, Any]:
        """Routes query based on computed complexity."""
        complexity = self.assess_complexity(query)

        if complexity < self.tau_param:
            route = "Route A (No-Retrieval Parametric)"
            action = "DIRECT_GENERATION"
        elif complexity < self.tau_agent:
            route = "Route B (Single-Step Local HBM RAG)"
            action = "SINGLE_STEP_RETRIEVAL"
        else:
            route = "Route C (Multi-Hop Agentic Loop)"
            action = "ITERATIVE_DECOMPOSITION"

        return {
            "query": query,
            "complexity_score": complexity,
            "route": route,
            "action": action,
            "device": str(self.device),
        }

    def decompose_multihop_query(self, query: str) -> List[str]:
        """Splits complex queries into sequential sub-queries."""
        delims = r"\s+(?:and then|after which|compared to|while|versus|and)\s+"
        parts = re.split(delims, query, flags=re.IGNORECASE)
        sub_queries = [p.strip() for p in parts if len(p.strip()) > 3]

        if len(sub_queries) <= 1:
            return [
                f"Sub-query 1: Identify foundational entities in '{query}'",
                f"Sub-query 2: Correlate cross-domain effects for '{query}'"
            ]

        return [f"Sub-query {i+1}: {sq}" for i, sq in enumerate(sub_queries)]


if __name__ == "__main__":
    print("[Winograd - Systems Architect] Standalone Adaptive RAG Router Test:")
    router = AdaptiveRAGRouter()
    print(f"Detected Compute Device: {router.device}")

    test_queries = [
        "What is the speed of light constant?",
        "Find the visual magnitude of Sanduleak -69 202 before 1987.",
        "Compare R136 UV radiation ionizing flux with neutrino pulse timings from Supernova 1987A and determine blast wave delay."
    ]

    for q in test_queries:
        res = router.route_query(q)
        print(f"\nQuery: '{q[:50]}...' -> {res['route']} (Complexity: {res['complexity_score']:.2f})")
