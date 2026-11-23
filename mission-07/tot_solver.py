"""
Mission 07: Part 1 - Systems Architect
Module: tot_solver.py
Cadet: Hassaan Ahmad Khawaja (Systems Architect)
Squadron: Winograd
Sector: SEC-07-SGR (Sagittarius A* Gravitational Horizon)

Description:
    Tree-of-Thoughts (ToT) Beam and Backtracking Search Engine
    with explicit expansion budget limits and pruning thresholds.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any


@dataclass
class ThoughtNode:
    """Represents a discrete reasoning thought step within the tree."""
    thought_state: str
    depth: int = 0
    step_score: float = 0.0
    cumulative_score: float = 0.0
    parent: Optional[ThoughtNode] = None
    children: List[ThoughtNode] = field(default_factory=list)

    def get_trajectory(self) -> List[str]:
        """Reconstructs the full sequence of thought states from root to this node."""
        path: List[str] = []
        curr: Optional[ThoughtNode] = self
        while curr is not None:
            path.append(curr.thought_state)
            curr = curr.parent
        return list(reversed(path))


class TreeOfThoughtsSolver:
    """Inference compute engine executing ToT Breadth-First Beam and Depth-First Backtracking."""

    def __init__(
        self,
        beam_width: int = 3,
        max_expansions: int = 20,
        prune_threshold: float = 0.40,
    ) -> None:
        self.beam_width = beam_width
        self.max_expansions = max_expansions
        self.prune_threshold = prune_threshold
        self.expansion_count = 0
        self.pruned_branches_count = 0

    def reset(self) -> None:
        self.expansion_count = 0
        self.pruned_branches_count = 0

    def bfs_beam_search(
        self,
        root: ThoughtNode,
        generator_fn: Callable[[ThoughtNode], List[str]],
        evaluator_fn: Callable[[str, ThoughtNode], float],
        max_depth: int = 4,
    ) -> ThoughtNode:
        """
        Executes Breadth-First Beam Search (ToT-BFS).
        Restricts frontier to at most beam_width nodes at each depth layer.
        """
        self.reset()
        active_beam: List[ThoughtNode] = [root]
        best_overall_node: ThoughtNode = root

        for current_depth in range(1, max_depth + 1):
            if not active_beam or self.expansion_count >= self.max_expansions:
                break

            candidates: List[ThoughtNode] = []
            for parent_node in active_beam:
                if self.expansion_count >= self.max_expansions:
                    break

                proposed_thoughts = generator_fn(parent_node)
                self.expansion_count += 1

                for t_str in proposed_thoughts:
                    val = evaluator_fn(t_str, parent_node)
                    child = ThoughtNode(
                        thought_state=t_str,
                        depth=current_depth,
                        step_score=val,
                        cumulative_score=parent_node.cumulative_score + val,
                        parent=parent_node,
                    )
                    parent_node.children.append(child)

                    if val < self.prune_threshold:
                        self.pruned_branches_count += 1
                        continue

                    candidates.append(child)

            if not candidates:
                break

            # Rank descending by step score and keep top-B
            candidates.sort(key=lambda n: n.step_score, reverse=True)
            active_beam = candidates[: self.beam_width]

            if active_beam and active_beam[0].step_score >= best_overall_node.step_score:
                best_overall_node = active_beam[0]

        return best_overall_node

    def dfs_backtrack_search(
        self,
        root: ThoughtNode,
        generator_fn: Callable[[ThoughtNode], List[str]],
        evaluator_fn: Callable[[str, ThoughtNode], float],
        max_depth: int = 4,
    ) -> ThoughtNode:
        """
        Executes Depth-First Backtracking Search (ToT-DFS).
        Explores highest scoring child branch; backtracks on sub-threshold evaluation or dead-ends.
        """
        self.reset()
        top_node: ThoughtNode = root

        def _traverse(node: ThoughtNode) -> Optional[ThoughtNode]:
            nonlocal top_node
            if node.depth >= max_depth or self.expansion_count >= self.max_expansions:
                return node

            branches = generator_fn(node)
            self.expansion_count += 1

            valid_children: List[ThoughtNode] = []
            for b_state in branches:
                score = evaluator_fn(b_state, node)
                child = ThoughtNode(
                    thought_state=b_state,
                    depth=node.depth + 1,
                    step_score=score,
                    cumulative_score=node.cumulative_score + score,
                    parent=node,
                )
                node.children.append(child)

                if score < self.prune_threshold:
                    self.pruned_branches_count += 1
                else:
                    valid_children.append(child)

            # Sort candidate branches descending
            valid_children.sort(key=lambda c: c.step_score, reverse=True)

            for cand in valid_children:
                if self.expansion_count >= self.max_expansions:
                    break
                res = _traverse(cand)
                if res and (res.step_score > top_node.step_score or top_node == root):
                    top_node = res

            return top_node

        _traverse(root)
        return top_node


if __name__ == "__main__":
    print("[Winograd - Systems Architect] Standalone ToT Solver Test:")
    r = ThoughtNode(thought_state="Root: Ingress vector at Sgr A* event horizon")

    def mock_gen(node: ThoughtNode) -> List[str]:
        return [
            f"{node.thought_state} -> Retro-burn thrusters",
            f"{node.thought_state} -> Direct radial descent (Deadly)",
            f"{node.thought_state} -> Relativistic frame-drag slingshot (Optimal)",
        ]

    def mock_eval(state: str, parent: ThoughtNode) -> float:
        if "Direct radial" in state:
            return 0.15
        elif "slingshot" in state:
            return 0.94
        return 0.60

    solver = TreeOfThoughtsSolver(beam_width=2, max_expansions=12, prune_threshold=0.40)
    top_bfs = solver.bfs_beam_search(r, mock_gen, mock_eval, max_depth=3)
    print(f"Top BFS Terminal State: {top_bfs.thought_state}")
    print(f"Step Score: {top_bfs.step_score:.2f}, Expansions: {solver.expansion_count}, Pruned: {solver.pruned_branches_count}")
