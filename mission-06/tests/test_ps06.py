"""
Master Test Suite for Squadron Winograd - Mission 06
Course: Conversational AI (Winter Semester 2026/27)
Squadron: Winograd
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pytest
import numpy as np

from importlib import import_module
fsm_module = import_module("01_Agent_State_Machine")
dispatcher_module = import_module("02_Tool_Protocol_Dispatcher")
mdp_module = import_module("03_MDP_Trajectory_and_Return")
sentinel_module = import_module("04_Cycle_Sentinel_and_System2")

AgentPhase = fsm_module.AgentPhase
AutonomousNavigatorStateMachine = fsm_module.AutonomousNavigatorStateMachine
WinogradToolDispatcher = dispatcher_module.WinogradToolDispatcher
MarkovDecisionTrajectoryLogger = mdp_module.MarkovDecisionTrajectoryLogger
FloydCycleSentinel = sentinel_module.FloydCycleSentinel
CryptographicStateActionTripwire = sentinel_module.CryptographicStateActionTripwire
System2DeliberationInterceptor = sentinel_module.System2DeliberationInterceptor


# ==========================================
# PART 1: Agent State Machine Tests
# ==========================================

def test_winograd_fsm_transitions():
    fsm = AutonomousNavigatorStateMachine(max_steps=20)
    assert fsm.context.current_phase == AgentPhase.STANDBY

    p1 = fsm.step()
    assert p1 == AgentPhase.SENSING
    p2 = fsm.step()
    assert p2 == AgentPhase.REASONING
    p3 = fsm.step()
    assert p3 == AgentPhase.DISPATCHING
    p4 = fsm.step()
    assert p4 == AgentPhase.AUDITING
    p5 = fsm.step()
    assert p5 == AgentPhase.EVALUATING


def test_winograd_fsm_budget_clamping():
    fsm = AutonomousNavigatorStateMachine(max_steps=10)
    for _ in range(15):
        fsm.step()

    assert fsm.context.step_count == 10
    assert fsm.context.current_phase == AgentPhase.TERMINATED
    assert fsm.context.is_halted is True
    assert "SAFETY TRIPWIRE TRIGGERED" in fsm.context.forced_termination_reason


# ==========================================
# PART 2: Tool Dispatcher & Exception Boundary
# ==========================================

def test_winograd_tool_dispatcher_success():
    disp = WinogradToolDispatcher()
    res = disp.dispatch("recalibrate_tachyon_grid", '{"power_mw": 500.0, "harmonics": 5}')
    data = json.loads(res)
    assert data["status"] == "SUCCESS"
    assert "500.0 MW" in data["output"]


def test_winograd_tool_dispatcher_validation_error():
    disp = WinogradToolDispatcher()
    # Missing required 'harmonics' parameter
    res = disp.dispatch("recalibrate_tachyon_grid", '{"power_mw": 500.0}')
    data = json.loads(res)
    assert data["status"] == "VALIDATION_ERROR"
    assert "Missing required parameter" in data["error"]


def test_winograd_tool_dispatcher_boundary_no_crash():
    disp = WinogradToolDispatcher()
    # Malformed JSON should not raise an unhandled exception
    res = disp.dispatch("inspect_deflector_matrix", "NOT_JSON")
    data = json.loads(res)
    assert data["status"] == "VALIDATION_ERROR"
    assert "Malformed JSON" in data["error"]


# ==========================================
# PART 3: MDP Return & Transition Probabilities
# ==========================================

def test_winograd_mdp_discounted_return():
    # Specification check: [10, 0, -5, 20] at gamma=0.95
    # G0 = 10(1) + 0(0.95) - 5(0.9025) + 20(0.857375) = 22.6350
    rewards = [10.0, 0.0, -5.0, 20.0]
    g0 = MarkovDecisionTrajectoryLogger.calculate_discounted_return_from_rewards(rewards, gamma=0.95)
    assert pytest.approx(g0, rel=1e-5) == 22.6350


def test_winograd_transition_matrix_normalization():
    logger = MarkovDecisionTrajectoryLogger(gamma=0.95)
    logger.record_transition("A", "act", 1.0, "B")
    logger.record_transition("B", "act", 2.0, "C")
    logger.record_transition("C", "act", 0.0, "A")
    logger.record_transition("B", "act", -1.0, "A")

    matrix, states = logger.estimate_transition_matrix()
    assert len(states) == 3
    # Check that row sums of non-zero rows are equal to 1.0
    row_sums = np.sum(matrix, axis=1)
    for s in row_sums:
        if s > 0:
            assert pytest.approx(s, rel=1e-5) == 1.0


# ==========================================
# PART 4: Cycle Sentinel & System 2 Engine
# ==========================================

def test_winograd_floyd_cycle_detection():
    # Sequence with period 3: [s1, s2, s3, s1, s2, s3...]
    stream = ["s1", "s2", "s3", "s1", "s2", "s3", "s1"]
    has_cycle, step_intercepted, period = FloydCycleSentinel.detect_periodic_cycle(stream)
    assert has_cycle is True
    assert step_intercepted == 6  # 6 < 10
    assert period == 3


def test_winograd_sha256_tripwire_and_system2():
    tripwire = CryptographicStateActionTripwire(repetition_threshold=3)

    # 1st and 2nd occurrence should not trip
    t1, _ = tripwire.inspect_and_record("SENSING", "Read", 1)
    t2, _ = tripwire.inspect_and_record("SENSING", "Read", 2)
    assert t1 is False
    assert t2 is False

    # 3rd occurrence must trip
    t3, alert = tripwire.inspect_and_record("SENSING", "Read", 3)
    assert t3 is True
    assert "REPETITIVE_CYCLE_INTERCEPTED" in alert

    # System 2 Interception
    sys2 = System2DeliberationInterceptor()
    plan = sys2.intervene_and_replan("SENSING", alert)
    assert plan["status"] == "SYSTEM_2_ENGAGED"
    assert plan["selected_action"] == "DIVERT_IMPULSE_MANIFOLD"
