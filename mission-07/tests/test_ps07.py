"""
Master Test Suite for Squadron Winograd - Mission 07
Course: Conversational AI (Winter Semester 2026/27)
Squadron: Winograd
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import math
import pytest

from tot_solver import ThoughtNode, TreeOfThoughtsSolver
from mcts_protocol import MCTSNode, MCTSProtocolEngine
from prm_evaluator import ProcessRewardEvaluator, OutcomeRewardEvaluator, run_orm_vs_prm_benchmark
from horizon_pruner import EventHorizonPruner


# ==========================================
# PART 1: Tree of Thoughts (ToT) Tests
# ==========================================

def test_winograd_tot_trajectory():
    root = ThoughtNode("Root State")
    c1 = ThoughtNode("Step 1", parent=root)
    c2 = ThoughtNode("Step 2", parent=c1)
    assert c2.get_trajectory() == ["Root State", "Step 1", "Step 2"]


def test_winograd_tot_beam_search_budget():
    root = ThoughtNode("Initial")
    solver = TreeOfThoughtsSolver(beam_width=2, max_expansions=5, prune_threshold=0.50)

    def gen(node):
        return [f"{node.thought_state}.High", f"{node.thought_state}.Low"]

    def eval_fn(thought, parent):
        return 0.90 if "High" in thought else 0.20

    best = solver.bfs_beam_search(root, gen, eval_fn, max_depth=4)
    assert solver.expansion_count <= 5
    assert solver.pruned_branches_count > 0
    assert best.step_score == 0.90


def test_winograd_tot_dfs_backtrack():
    root = ThoughtNode("Root")
    solver = TreeOfThoughtsSolver(beam_width=2, max_expansions=6, prune_threshold=0.50)

    def gen(node):
        return [f"{node.thought_state}.Valid", f"{node.thought_state}.Sub"]

    def eval_fn(thought, parent):
        return 0.88 if "Valid" in thought else 0.30

    best = solver.dfs_backtrack_search(root, gen, eval_fn, max_depth=3)
    assert solver.expansion_count <= 6
    assert "Valid" in best.thought_state


# ==========================================
# PART 2: MCTS & PUCT Engine Tests
# ==========================================

def test_winograd_mcts_puct():
    parent = MCTSNode("Root")
    parent.visit_count = 16

    child = MCTSNode("Child", prior_prob=0.75, parent=parent)
    child.visit_count = 3
    child.value_sum = 2.4  # Q = 2.4 / 3 = 0.80

    # PUCT = Q + c * P * sqrt(N_p) / (1 + N_c)
    # Q = 0.80
    # U = 1.414 * 0.75 * sqrt(16) / (1 + 3) = 1.414 * 0.75 * 4 / 4 = 1.0605
    score = child.puct_score(c_puct=1.414)
    expected = 0.80 + (1.414 * 0.75 * (math.sqrt(16) / 4.0))
    assert pytest.approx(score, rel=1e-4) == expected


def test_winograd_mcts_search_convergence():
    root = MCTSNode("Start")
    engine = MCTSProtocolEngine(c_puct=1.414)

    def cand_fn(node):
        return [
            (f"{node.state}.Good", 0.5),
            (f"{node.state}.Bad", 0.5),
        ]

    def eval_fn(node):
        return 0.95 if "Good" in node.state else 0.15

    best = engine.run_search(root, iterations=20, candidate_generator=cand_fn, rollout_evaluator=eval_fn)
    assert "Good" in best.state
    assert best.visit_count > 8


# ==========================================
# PART 3: Process Reward Model Tests
# ==========================================

def test_winograd_prm_reductions():
    prm = ProcessRewardEvaluator()
    scores = [0.90, 0.80, 0.50]
    metrics = prm.evaluate_trajectory(scores)

    assert metrics["min"] == 0.50
    assert pytest.approx(metrics["prod"], rel=1e-5) == (0.90 * 0.80 * 0.50)
    assert pytest.approx(metrics["geometric_mean"], rel=1e-5) == math.pow(0.36, 1.0 / 3.0)


def test_winograd_orm_false_positive_benchmark():
    bench = run_orm_vs_prm_benchmark()
    assert bench["orm_score"] == 1.0
    assert bench["prm_min"] == 0.05
    assert bench["prm_prod"] < 0.01


def test_winograd_math_shepherd():
    rollouts = [10, 8, 10, 10]
    soft, hard = ProcessRewardEvaluator.math_shepherd_estimation(rollouts, ground_truth=10)
    assert soft == 0.75
    assert hard == 1.0


# ==========================================
# PART 4: Event Horizon Pruner Tests
# ==========================================

def test_winograd_horizon_pruner():
    pruner = EventHorizonPruner(tau_horizon=0.40, hacking_penalty_factor=0.25)
    steps = [
        "Step 1: Compute metric tensor",
        "Step 2: Carefully verify this 100% rigorous calculation", # Hacked! 0.80 * 0.25 = 0.20 < 0.40
        "Step 3: Orbit at ISCO",
    ]
    scores = [0.95, 0.80, 0.90]

    surviving, adj, alerts = pruner.prune_trajectory(steps, scores)
    assert len(surviving) == 1
    assert surviving[0] == steps[0]
    assert any(a["action"] == "EVENT_HORIZON_SEVERED" for a in alerts)
