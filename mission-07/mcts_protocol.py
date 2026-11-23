"""
Mission 07: Part 2 - Communications & Protocol Officer
Module: mcts_protocol.py
Cadet: Muhammad Usman Maratib (Communications & Protocol Officer)
Squadron: Winograd
Sector: SEC-07-SGR (Sagittarius A* Gravitational Horizon)

Description:
    4-Phase Monte Carlo Tree Search (MCTS) Engine guided by LLM policy priors
    and the PUCT (Predictor + Upper Confidence Bound for Trees) selection rule.
"""

from __future__ import annotations
import math
from typing import List, Optional, Tuple, Callable, Dict, Any


class MCTSNode:
    """Represents an MCTS search node with visit statistics and policy priors."""

    def __init__(
        self,
        state: str,
        prior_prob: float = 1.0,
        parent: Optional[MCTSNode] = None,
    ) -> None:
        self.state: str = state
        self.prior_prob: float = prior_prob
        self.parent: Optional[MCTSNode] = parent
        self.children: List[MCTSNode] = []
        self.visit_count: int = 0
        self.value_sum: float = 0.0

    @property
    def q_value(self) -> float:
        """Mean action value Q(s, a) = W(s, a) / N(s, a)."""
        if self.visit_count == 0:
            return 0.0
        return self.value_sum / float(self.visit_count)

    def puct_score(self, c_puct: float = 1.414) -> float:
        """
        Computes the PUCT selection score:
            PUCT(s, a) = Q(s, a) + c_puct * P(a|s) * sqrt(N(s)) / (1 + N(s, a))
        """
        q = self.q_value
        parent_visits = self.parent.visit_count if self.parent is not None else 1
        n_parent = max(1, parent_visits)
        exploration = c_puct * self.prior_prob * (math.sqrt(n_parent) / (1.0 + self.visit_count))
        return q + exploration

    def select_best_child(self, c_puct: float = 1.414) -> MCTSNode:
        """Selects child with maximal PUCT score."""
        if not self.children:
            raise ValueError("Childless node cannot select best child.")
        return max(self.children, key=lambda c: c.puct_score(c_puct))

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def get_trajectory(self) -> List[str]:
        path: List[str] = []
        curr: Optional[MCTSNode] = self
        while curr is not None:
            path.append(curr.state)
            curr = curr.parent
        return list(reversed(path))


class MCTSProtocolEngine:
    """Orchestrates the 4 canonical MCTS phases: Selection, Expansion, Simulation, Backprop."""

    def __init__(self, c_puct: float = 1.414) -> None:
        self.c_puct = c_puct

    def select_leaf(self, root: MCTSNode) -> MCTSNode:
        """Phase 1: Greedily selects child nodes with highest PUCT score until a leaf is reached."""
        curr = root
        while not curr.is_leaf():
            curr = curr.select_best_child(self.c_puct)
        return curr

    def expand(
        self,
        node: MCTSNode,
        candidate_priors: List[Tuple[str, float]],
    ) -> List[MCTSNode]:
        """Phase 2: Instantiates child nodes from candidate (state, prior_probability) tuples."""
        if node.children:
            return node.children

        for state_text, prior in candidate_priors:
            child = MCTSNode(state=state_text, prior_prob=prior, parent=node)
            node.children.append(child)
        return node.children

    def simulate_rollout(
        self,
        node: MCTSNode,
        rollout_evaluator: Callable[[MCTSNode], float],
    ) -> float:
        """Phase 3: Computes simulated rollout value or PRM quality estimate in [0, 1]."""
        raw_val = rollout_evaluator(node)
        return max(0.0, min(1.0, float(raw_val)))

    def backpropagate(self, node: MCTSNode, reward: float) -> None:
        """Phase 4: Traverses upward, incrementing visit count and accumulating value sum."""
        curr: Optional[MCTSNode] = node
        while curr is not None:
            curr.visit_count += 1
            curr.value_sum += reward
            curr = curr.parent

    def run_search(
        self,
        root: MCTSNode,
        iterations: int,
        candidate_generator: Callable[[MCTSNode], List[Tuple[str, float]]],
        rollout_evaluator: Callable[[MCTSNode], float],
    ) -> MCTSNode:
        """Runs MCTS for specified iterations and returns child with highest visit count."""
        for _ in range(iterations):
            leaf = self.select_leaf(root)

            if leaf.visit_count > 0 or leaf == root:
                candidates = candidate_generator(leaf)
                if candidates:
                    children = self.expand(leaf, candidates)
                    leaf = children[0]

            val = self.simulate_rollout(leaf, rollout_evaluator)
            self.backpropagate(leaf, val)

        if not root.children:
            return root
        return max(root.children, key=lambda c: c.visit_count)


if __name__ == "__main__":
    print("[Winograd - Protocol Officer] Standalone MCTS Protocol Test:")
    r = MCTSNode(state="Sgr A* Horizon Ingress")
    engine = MCTSProtocolEngine(c_puct=1.414)

    def mock_cand(node: MCTSNode):
        return [
            (f"{node.state} -> Route 1: Magnetic reconnection channel", 0.7),
            (f"{node.state} -> Route 2: High shear accretion path", 0.1),
            (f"{node.state} -> Route 3: Standard orbital clearance", 0.2),
        ]

    def mock_eval(node: MCTSNode):
        if "Magnetic reconnection" in node.state:
            return 0.92
        elif "High shear" in node.state:
            return 0.10
        return 0.50

    best_node = engine.run_search(r, iterations=25, candidate_generator=mock_cand, rollout_evaluator=mock_eval)
    print(f"Selected Action: {best_node.state}")
    print(f"Visits: {best_node.visit_count}, Q-value: {best_node.q_value:.4f}")
