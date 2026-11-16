"""
Mission 05 — Part 2: Communications & Protocol Officer
Lexical Okapi BM25 Scorer & Reciprocal Rank Fusion (RRF) Hybrid Pipeline

Starship Operational Unit: USSE Noosphere Bridge Crew
Waypoint: Crab Pulsar Remnant / Messier 1 (SEC-05-M01)
Subsystem 05: Dual-Path Associative Memory Core
Cadet Assigned: Muhammad Usman Maratib (Communications & Protocol Officer)
Squadron: Squadron Winograd
"""

import math
import re
from collections import Counter
from typing import List, Dict, Tuple, Set


class WinogradBM25Engine:
    """
    Okapi BM25 Lexical Scorer configured to preserve critical serial codes
    against dense vector semantic dilution (Robertson & Jones 1976).
    Formula:
      BM25(D, Q) = sum_{q in Q} IDF(q) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (|D| / avgdl)))
    """
    def __init__(self, document_corpus: List[str], k1_param: float = 1.5, b_param: float = 0.75):
        self.k1 = k1_param
        self.b = b_param
        self.raw_documents = document_corpus
        self.total_docs = len(document_corpus)
        self.tokenized_docs = [self._extract_tokens(doc) for doc in document_corpus]
        self.lengths = [len(tokens) for tokens in self.tokenized_docs]
        self.average_length = sum(self.lengths) / float(max(self.total_docs, 1))

        # Build Document Frequency map
        self.doc_frequency: Dict[str, int] = Counter()
        for doc_tokens in self.tokenized_docs:
            for term in set(doc_tokens):
                self.doc_frequency[term] += 1

        # Precompute Robertson-Spärck Jones IDF
        self.idf_cache: Dict[str, float] = {}
        for term, df_val in self.doc_frequency.items():
            # Standard smoothed IDF
            self.idf_cache[term] = math.log(1.0 + (self.total_docs - df_val + 0.5) / (df_val + 0.5))

    @staticmethod
    def _extract_tokens(raw_string: str) -> List[str]:
        """Separates punctuation while keeping hyphenated alphanumeric part codes intact."""
        lowered = raw_string.lower()
        # Find alphanumeric words and codes
        tokens = re.findall(r"\b[a-z0-9]+(?:-[a-z0-9]+)*\b", lowered)
        return tokens

    def search_scores(self, search_query: str) -> List[Tuple[int, float]]:
        """Scores all documents against search_query terms."""
        query_tokens = self._extract_tokens(search_query)
        scored_records = []

        for doc_idx, doc_tokens in enumerate(self.tokenized_docs):
            doc_len = self.lengths[doc_idx]
            term_counts = Counter(doc_tokens)
            doc_score = 0.0

            for q_term in query_tokens:
                if q_term in term_counts:
                    freq = term_counts[q_term]
                    idf = self.idf_cache.get(q_term, 0.0)
                    length_penalty = 1.0 - self.b + self.b * (doc_len / max(self.average_length, 1e-9))
                    tf_component = (freq * (self.k1 + 1.0)) / (freq + self.k1 * length_penalty)
                    doc_score += idf * tf_component

            scored_records.append((doc_idx, float(doc_score)))

        scored_records.sort(key=lambda item: item[1], reverse=True)
        return scored_records


def combine_rankings_rrf(
    dense_candidate_ids: List[int],
    sparse_candidate_ids: List[int],
    fusion_k: int = 60
) -> List[Tuple[int, float]]:
    """
    Executes Reciprocal Rank Fusion (RRF) to merge dual retrieval pathways.
    RRF(d) = sum_{stream} 1 / (fusion_k + rank(d))
    """
    composite_scores: Dict[int, float] = {}

    for dense_pos, doc_id in enumerate(dense_candidate_ids):
        rank_1based = dense_pos + 1
        composite_scores[doc_id] = composite_scores.get(doc_id, 0.0) + (1.0 / (fusion_k + rank_1based))

    for sparse_pos, doc_id in enumerate(sparse_candidate_ids):
        rank_1based = sparse_pos + 1
        composite_scores[doc_id] = composite_scores.get(doc_id, 0.0) + (1.0 / (fusion_k + rank_1based))

    final_ranking = sorted(composite_scores.items(), key=lambda pair: pair[1], reverse=True)
    return final_ranking


class HybridRetrievalPipeline:
    """
    Coordinates lexical BM25 and dense representation rank streams.
    """
    def __init__(self, corpus: List[str], rrf_k: int = 60):
        self.corpus = corpus
        self.bm25_core = WinogradBM25Engine(corpus)
        self.rrf_k = rrf_k

    def retrieve(self, query: str, dense_ordered_ids: List[int], top_results: int = 3) -> List[Dict]:
        sparse_matches = self.bm25_core.search_scores(query)
        sparse_ordered_ids = [doc_id for doc_id, _ in sparse_matches]

        fused_scores = combine_rankings_rrf(dense_ordered_ids, sparse_ordered_ids, fusion_k=self.rrf_k)
        output = []
        for doc_id, rrf_val in fused_scores[:top_results]:
            bm25_val = next((sc for did, sc in sparse_matches if did == doc_id), 0.0)
            output.append({
                "doc_id": doc_id,
                "rrf_score": rrf_val,
                "bm25_score": bm25_val,
                "document_text": self.corpus[doc_id]
            })
        return output


if __name__ == "__main__":
    print("=== SQUADRON WINOGRAD: BM25 & RECIPROCAL RANK FUSION ===")
    sample_corpus = [
        "AURA Subsystem 05 associative memory core undergoing Crab Pulsar calibration.",
        "Primary magnetic deflector shield harmonic code is MAG-SHIELD-77B at 30.22 Hz.",
        "Warp vector plasma manifold alignment requires exact code PR-882-HEX.",
        "Cryo-coolant emergency valve designated VLV-904-CRY for antimatter chill loop.",
        "General telemetry archives indicate no coronal flares detected in Taurus filament."
    ]

    pipeline = HybridRetrievalPipeline(sample_corpus, rrf_k=60)
    query_target = "PR-882-HEX plasma alignment"

    # Dense heuristic ranking (simulating vector cluster overlap)
    simulated_dense = [0, 2, 1, 3, 4]
    fused_results = pipeline.retrieve(query_target, simulated_dense, top_results=2)

    for item in fused_results:
        print(f"Doc {item['doc_id']} | RRF Score: {item['rrf_score']:.6f} | BM25: {item['bm25_score']:.3f}")
        print(f"  Excerpt: {item['document_text']}")
