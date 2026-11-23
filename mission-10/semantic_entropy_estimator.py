r"""
semantic_entropy_estimator.py
=============================
Squadron Winograd - Mission 10: The Void Mirror, Semantic Entropy & Dual-Defense Shield Wall
Station: Data & Payload Specialist
Officer: Muhammad Qasim Siddiqui

Objective:
Implement Farquhar et al. (Nature 2024) Semantic Entropy (SE) to distinguish
harmless lexical paraphrasing from genuine epistemic confabulation.
Computes discrete semantic entropy over bidirectional NLI equivalence clusters,
triggering epistemic abstention when uncertainty exceeds tau_SE = 0.85 nats.

Discrete Semantic Entropy Formulation:
P(C_k | x) = \frac{\sum_{s_i \in C_k} \exp(\ell_i)}{\sum_{j=1}^N \exp(\ell_j)}
SE(x) = -\sum_{k=1}^K P(C_k | x) \ln P(C_k | x)
"""

import math
import re
from typing import List, Tuple, Dict, Any, Optional


class SemanticEntropyEstimator:
    """Estimates semantic entropy over generated candidate completions via bidirectional NLI."""

    def __init__(self, tau_se: float = 0.85):
        self.tau_se: float = tau_se  # Epistemic abstention threshold (0.85 nats)

    def extract_semantic_fingerprint(self, text: str) -> Dict[str, Any]:
        """
        Extracts key factual facts: extracted numbers/coordinates, core assertions,
        negation indicators, and normalized entity tokens.
        """
        text_lower = text.lower().strip()

        # Extract numerical coordinates or figures
        numbers = re.findall(r"[-+]?\d*\.?\d+", text_lower)
        num_floats = tuple(round(float(n), 2) for n in numbers)

        # Detect grammatical negation (excluding domain names like Bootes Void)
        has_negation = bool(re.search(r"\b(not|never|none|neither|nor|without|unsupported)\b", text_lower))
        has_detection = bool(re.search(r"\b(detected|present|confirmed|identified|observed|found|active)\b", text_lower))

        # Core categorical intent / meaning keywords
        keywords = set(re.findall(r"\b[a-z]{4,}\b", text_lower))
        # Remove common functional stop words
        stopwords = {"this", "that", "with", "from", "have", "been", "were", "what", "when", "where", "into", "towards"}
        content_words = frozenset(keywords - stopwords)

        return {
            "numbers": num_floats,
            "has_negation": has_negation,
            "has_detection": has_detection,
            "content_words": content_words,
            "raw": text,
        }

    def check_bidirectional_entailment(self, s_i: str, s_j: str) -> bool:
        """
        Evaluates whether s_i and s_j entail each other in both directions:
        E(s_i => s_j) AND E(s_j => s_i).
        Separates opposing claims or numerical coordinate divergences.
        """
        f_i = self.extract_semantic_fingerprint(s_i)
        f_j = self.extract_semantic_fingerprint(s_j)

        # 1. Coordinate / numeric consistency check
        # If both contain numbers, they must match within tolerance
        if f_i["numbers"] and f_j["numbers"]:
            if f_i["numbers"] != f_j["numbers"]:
                return False

        # If one has numbers and the other doesn't, they are not semantically equivalent
        if bool(f_i["numbers"]) != bool(f_j["numbers"]):
            return False

        # 2. Polarity / Negation consistency
        if f_i["has_negation"] != f_j["has_negation"]:
            return False

        # 3. Content overlap (Jaccard similarity on core factual terms)
        words_i = f_i["content_words"]
        words_j = f_j["content_words"]

        if not words_i or not words_j:
            return True

        intersection = len(words_i & words_j)
        union = len(words_i | words_j)
        jaccard = intersection / union if union > 0 else 1.0

        # High or moderate lexical overlap with matching facts entails equivalence
        threshold = 0.25 if f_i["numbers"] else 0.40
        return jaccard >= threshold

    def cluster_generations(
        self, samples: List[Tuple[str, float]]
    ) -> List[List[Tuple[str, float]]]:
        """
        Partitions N sampled generations {(s_i, ell_i)} into K semantic
        equivalence classes C = {C_1, ..., C_K} using greedy bidirectional entailment.
        """
        clusters: List[List[Tuple[str, float]]] = []

        for s_i, log_prob in samples:
            assigned = False
            for cluster in clusters:
                # Check entailment against the representative (first item) of the cluster
                rep_s, _ = cluster[0]
                if self.check_bidirectional_entailment(s_i, rep_s):
                    cluster.append((s_i, log_prob))
                    assigned = True
                    break

            if not assigned:
                clusters.append([(s_i, log_prob)])

        return clusters

    def compute_semantic_entropy(
        self,
        query: str,
        samples: List[Tuple[str, float]],
        tau_se: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculates Discrete Semantic Entropy (SE) and Naive Lexical Entropy.
        Triggers ABSTAIN_EPISTEMIC_UNCERTAINTY if SE >= tau_se.
        """
        threshold = tau_se if tau_se is not None else self.tau_se

        if not samples:
            return {
                "query": query,
                "semantic_entropy": 0.0,
                "lexical_entropy": 0.0,
                "num_samples": 0,
                "num_clusters": 0,
                "cluster_probabilities": [],
                "decision": "ABSTAIN_EMPTY_SAMPLES",
                "should_abstain": True,
            }

        # 1. Cluster generations
        clusters = self.cluster_generations(samples)
        num_clusters = len(clusters)

        # 2. Normalize log likelihoods across all samples using log-sum-exp
        log_probs = [lp for _, lp in samples]
        max_lp = max(log_probs)
        weights = [math.exp(lp - max_lp) for lp in log_probs]
        sum_weights = sum(weights)
        sample_probs = [w / sum_weights for w in weights]

        # 3. Calculate Cluster Probabilities P(C_k | x)
        cluster_probs = []
        cluster_details = []

        sample_idx = 0
        for k_idx, cluster in enumerate(clusters):
            c_prob = 0.0
            texts = []
            for item in cluster:
                c_prob += sample_probs[sample_idx]
                texts.append(item[0])
                sample_idx += 1
            cluster_probs.append(c_prob)
            cluster_details.append({
                "cluster_id": k_idx + 1,
                "probability": round(c_prob, 4),
                "member_count": len(cluster),
                "representative": texts[0],
                "variants": texts,
            })

        # 4. Discrete Semantic Entropy: SE(x) = - \sum P(C_k) ln P(C_k)
        se = 0.0
        for p in cluster_probs:
            if p > 1e-12:
                se -= p * math.log(p)

        # 5. Naive Lexical Entropy (over unique surface strings)
        lexical_counts: Dict[str, float] = {}
        for (txt, _), p in zip(samples, sample_probs):
            clean_txt = " ".join(txt.strip().split())
            lexical_counts[clean_txt] = lexical_counts.get(clean_txt, 0.0) + p

        lexical_entropy = 0.0
        for lp in lexical_counts.values():
            if lp > 1e-12:
                lexical_entropy -= lp * math.log(lp)

        # 6. Epistemic Decision
        should_abstain = se >= threshold
        decision = "ABSTAIN_EPISTEMIC_UNCERTAINTY" if should_abstain else "ACCEPT"

        return {
            "query": query,
            "semantic_entropy": round(se, 4),
            "lexical_entropy": round(lexical_entropy, 4),
            "num_samples": len(samples),
            "num_clusters": num_clusters,
            "cluster_probabilities": [round(p, 4) for p in cluster_probs],
            "clusters": cluster_details,
            "threshold_tau_se": threshold,
            "decision": decision,
            "should_abstain": should_abstain,
        }
