"""
Mission 08: Part 3 - Data & Payload Specialist
Module: memgpt_pager.py
Cadet: Muhammad Qasim Siddiqui (Data & Payload Specialist)
Squadron: Winograd
Sector: SEC-08-CYG (Cygnus X-1 Accretion Corona)

Description:
    MemGPT Virtual Context Pager (OS-style context management):
    Core memory management, FIFO queue with tau_warn (0.70) pressure interrupts,
    and Generative Agents tri-factor retrieval scoring S(m, q).
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional


@dataclass
class ArchivalMemoryNode:
    """Represents an archived memory node in external storage."""
    id: int
    content: str
    importance: float              # I(m) in [1.0, 10.0]
    embedding: List[float]         # Vector representation e_m
    last_accessed_hours: float     # Delta t(m) hours elapsed


class MemGPTPager:
    """
    OS-style Virtual Context Manager:
    Core Memory (Registers) + FIFO Queue (L1 Cache) + Archival Store (Disk Virtual Memory).
    """

    def __init__(
        self,
        token_budget: int = 1000,
        tau_warn: float = 0.70,
        gamma_decay: float = 0.99,
        alpha_rec: float = 1.0,
        alpha_imp: float = 1.0,
        alpha_rel: float = 1.0,
    ) -> None:
        self.token_budget = token_budget
        self.tau_warn = tau_warn
        self.gamma_decay = gamma_decay
        self.alpha_rec = alpha_rec
        self.alpha_imp = alpha_imp
        self.alpha_rel = alpha_rel

        self.core_memory: Dict[str, str] = {}
        self.fifo_queue: List[str] = []
        self.archival_store: List[ArchivalMemoryNode] = []
        self.counter = 0
        self.alerts: List[str] = []

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()) + len(text) // 16)

    def current_token_usage(self) -> int:
        c_tokens = sum(self._estimate_tokens(f"{k}: {v}") for k, v in self.core_memory.items())
        f_tokens = sum(self._estimate_tokens(msg) for msg in self.fifo_queue)
        return c_tokens + f_tokens

    def core_memory_append(self, key: str, value: str) -> None:
        if key in self.core_memory:
            self.core_memory[key] += f"; {value}"
        else:
            self.core_memory[key] = value

    def core_memory_replace(self, key: str, old_val: str, new_val: str) -> bool:
        if key in self.core_memory and old_val in self.core_memory[key]:
            self.core_memory[key] = self.core_memory[key].replace(old_val, new_val)
            return True
        return False

    def check_memory_pressure(self) -> bool:
        """
        Monitors active token utilization.
        When usage / budget >= tau_warn (0.70), raises an interrupt and flushes
        the oldest 50% of the FIFO queue into archival memory.
        """
        usage = self.current_token_usage()
        ratio = usage / float(self.token_budget)

        if ratio >= self.tau_warn:
            alert = (
                f"[INTERRUPT] Memory pressure: {usage}/{self.token_budget} tokens "
                f"({ratio*100:.1f}%) >= tau_warn ({self.tau_warn*100:.0f}%). "
                f"Flushing oldest 50% FIFO buffer to archival storage."
            )
            self.alerts.append(alert)

            flush_n = max(1, len(self.fifo_queue) // 2)
            flushed = self.fifo_queue[:flush_n]
            self.fifo_queue = self.fifo_queue[flush_n:]

            summary = " [CONSOLIDATED FLUSH]: " + " | ".join(flushed)
            self.archival_memory_insert(
                content=summary,
                importance=7.0,
                embedding=[0.5, 0.5, 0.5, 0.5],
                last_accessed_hours=0.0,
            )
            return True

        return False

    def archival_memory_insert(
        self,
        content: str,
        importance: float,
        embedding: List[float],
        last_accessed_hours: float = 0.0,
    ) -> ArchivalMemoryNode:
        self.counter += 1
        node = ArchivalMemoryNode(
            id=self.counter,
            content=content,
            importance=max(1.0, min(10.0, float(importance))),
            embedding=embedding,
            last_accessed_hours=last_accessed_hours,
        )
        self.archival_store.append(node)
        return node

    @staticmethod
    def _cosine_sim(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        return dot / (norm1 * norm2) if (norm1 > 0 and norm2 > 0) else 0.0

    def score_memory(self, node: ArchivalMemoryNode, query_embedding: List[float]) -> float:
        """
        Park et al. (2023) Tri-Factor Retrieval Function:
            S(m, q) = alpha_rec * gamma^(Delta t(m)) + alpha_imp * (I(m) / 10) + alpha_rel * cos_sim(e_m, e_q)
        """
        recency = math.pow(self.gamma_decay, node.last_accessed_hours)
        importance = node.importance / 10.0
        relevance = self._cosine_sim(node.embedding, query_embedding)

        return (
            self.alpha_rec * recency
            + self.alpha_imp * importance
            + self.alpha_rel * relevance
        )

    def archival_memory_search(
        self,
        query_embedding: List[float],
        top_k: int = 3,
    ) -> List[Tuple[ArchivalMemoryNode, float]]:
        ranked = [
            (node, self.score_memory(node, query_embedding))
            for node in self.archival_store
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


if __name__ == "__main__":
    print("[Winograd - Data Specialist] Standalone MemGPT Pager Test:")
    pager = MemGPTPager(token_budget=100, tau_warn=0.70)
    pager.core_memory_append("Persona", "AURA Autonomous Stellar Nav AI")

    for i in range(10):
        pager.fifo_queue.append(f"Telemetry log packet {i}: Flare radiation measurement reading = {1000 + i * 20} keV.")
        pager.check_memory_pressure()

    print(f"Usage: {pager.current_token_usage()}/{pager.token_budget} | Remaining FIFO: {len(pager.fifo_queue)}")
    print(f"Archived Nodes: {len(pager.archival_store)} | Alerts: {len(pager.alerts)}")
