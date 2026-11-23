"""
Mission 09: Part 2 - Communications & Protocol Officer
Module: crag_selfrag_protocol.py
Cadet: Muhammad Usman Maratib (Communications & Protocol Officer)
Squadron: Winograd
Sector: SEC-09-LMC (Large Magellanic Cloud - Tarantula Nebula & SN 1987A)

Description:
    Corrective RAG (CRAG) Tri-Band Action Evaluator & Self-RAG Reflection Critique Scorer.
    Purifies retrieved documents into atomic sentence strips and scores generation beams
    over special reflection tokens ([ISREL], [ISSUP], [ISUSE]).
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple


class CRAGEvaluator:
    """
    Corrective RAG (CRAG) Confidence Evaluator:
    - CORRECT (max s_i >= 0.72): Decompose & strip-filter local chunks.
    - AMBIGUOUS (0.38 <= max s_i < 0.72): Local strips + relay reformulation.
    - INCORRECT (max s_i < 0.38): Discard local context & trigger external relay search.
    """

    def __init__(self, alpha_upper: float = 0.72, alpha_lower: float = 0.38) -> None:
        self.alpha_upper = alpha_upper
        self.alpha_lower = alpha_lower

    def evaluate_and_action(
        self,
        query: str,
        retrieved_chunks: List[Tuple[str, float]],
    ) -> Dict[str, Any]:
        if not retrieved_chunks:
            max_score = 0.0
            best_chunk = ""
        else:
            best_chunk, max_score = max(retrieved_chunks, key=lambda c: c[1])

        if max_score >= self.alpha_upper:
            action = "CORRECT"
            directive = "Decompose and strip-filter local chunks into atomic evidence."
        elif max_score >= self.alpha_lower:
            action = "AMBIGUOUS"
            directive = "Retain filtered local strips and trigger external LMC Relay query reformulation."
        else:
            action = "INCORRECT"
            directive = "Discard local chunks as noise; execute dedicated Tarantula Relay search."

        return {
            "query": query,
            "max_confidence": max_score,
            "best_chunk": best_chunk,
            "action": action,
            "directive": directive,
        }

    @staticmethod
    def decompose_and_filter_strips(
        doc_text: str,
        query: str,
        threshold: float = 0.25,
    ) -> List[str]:
        """Splits document into sentence strips and filters out noise via query term overlap."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", doc_text) if s.strip()]
        q_terms = set(re.findall(r"\w+", query.lower()))

        purified: List[str] = []
        for sentence in sentences:
            s_terms = set(re.findall(r"\w+", sentence.lower()))
            if not s_terms or not q_terms:
                continue

            overlap = len(q_terms.intersection(s_terms))
            score = overlap / float(len(q_terms))

            if score >= threshold:
                purified.append(sentence)

        return purified if purified else sentences[:1]


class SelfRAGCritiqueScorer:
    """
    Ranks generation candidate beams using Self-RAG reflection token critiques:
        Score(y) = log P(y | x, D) + w_rel * S([ISREL]) + w_sup * S([ISSUP]) + w_use * S([ISUSE])
    """

    def __init__(self, w_rel: float = 1.0, w_sup: float = 1.0, w_use: float = 0.5) -> None:
        self.w_rel = w_rel
        self.w_sup = w_sup
        self.w_use = w_use

    def score_candidate_beam(
        self,
        candidate_text: str,
        log_prob: float,
        is_relevant: float,
        is_supported: float,
        is_useful: float,
    ) -> Dict[str, Any]:
        norm_use = is_useful / 5.0 if is_useful > 1.0 else is_useful
        composite = (
            log_prob
            + (self.w_rel * is_relevant)
            + (self.w_sup * is_supported)
            + (self.w_use * norm_use)
        )
        return {
            "candidate": candidate_text,
            "log_prob": log_prob,
            "is_rel": is_relevant,
            "is_sup": is_supported,
            "is_use": norm_use,
            "composite_score": composite,
        }


if __name__ == "__main__":
    print("[Winograd - Protocol Officer] Standalone CRAG & Self-RAG Test:")
    crag = CRAGEvaluator()
    chunks = [
        ("Sanduleak -69 202 was a B3 Ia blue supergiant star in the Tarantula Nebula.", 0.88),
        ("Supernova 1987A occurred on 23 February 1987 in 30 Doradus.", 0.91),
    ]
    res = crag.evaluate_and_action("What was the progenitor star of SN 1987A?", chunks)
    print(f"Action: {res['action']} (Score: {res['max_confidence']:.2f}) -> {res['directive']}")
