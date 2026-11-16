"""
Mission 06: Part 1 - Systems Architect
Module: 01_Agent_State_Machine.py
Cadet: Hassaan Ahmad Khawaja (Systems Architect)
Squadron: Winograd
Sector: SEC-06-CAR (Eta Carinae Manifold Ingress)

Description:
    Autonomous Agent State Machine with deterministic step transitions,
    epistemic state tracking, and strict step-budget safety clamps (N <= 20).
"""

from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


class AgentPhase(Enum):
    """Discrete operational phases of the Winograd Autonomous Agent."""
    STANDBY = auto()       # Initial idle / waiting phase
    SENSING = auto()       # Perceptual telemetry acquisition
    REASONING = auto()     # Deliberation and cognitive planning
    DISPATCHING = auto()   # Tool action emission
    AUDITING = auto()      # Sensor observation & result validation
    EVALUATING = auto()    # Self-reflection and goal assessment
    TERMINATED = auto()    # Safe halted state


@dataclass
class AgentExecutionContext:
    """Stores persistent execution state and telemetry across operational steps."""
    step_count: int = 0
    max_step_limit: int = 20
    current_phase: AgentPhase = AgentPhase.STANDBY
    state_trajectory: List[AgentPhase] = field(default_factory=list)
    memory_buffer: List[Dict[str, Any]] = field(default_factory=list)
    is_halted: bool = False
    forced_termination_reason: Optional[str] = None


class AutonomousNavigatorStateMachine:
    """Deterministic finite state machine controlling agent phase transitions."""

    # Allowed forward transition topology
    TRANSITION_MAP: Dict[AgentPhase, List[AgentPhase]] = {
        AgentPhase.STANDBY: [AgentPhase.SENSING],
        AgentPhase.SENSING: [AgentPhase.REASONING],
        AgentPhase.REASONING: [AgentPhase.DISPATCHING, AgentPhase.TERMINATED],
        AgentPhase.DISPATCHING: [AgentPhase.AUDITING],
        AgentPhase.AUDITING: [AgentPhase.EVALUATING],
        AgentPhase.EVALUATING: [AgentPhase.REASONING, AgentPhase.TERMINATED],
        AgentPhase.TERMINATED: [],
    }

    def __init__(self, max_steps: int = 20) -> None:
        self.context = AgentExecutionContext(max_step_limit=max_steps)
        self.context.state_trajectory.append(AgentPhase.STANDBY)

    def step(self, perception_data: Optional[Dict[str, Any]] = None, goal_achieved: bool = False) -> AgentPhase:
        """
        Executes a single discrete cognitive step.
        Enforces hard ceiling N <= max_step_limit to prevent runaway infinite loops.
        """
        if self.context.is_halted:
            return self.context.current_phase

        self.context.step_count += 1

        # Security Tripwire: Hard step budget check
        if self.context.step_count >= self.context.max_step_limit:
            self.context.current_phase = AgentPhase.TERMINATED
            self.context.is_halted = True
            self.context.forced_termination_reason = (
                f"SAFETY TRIPWIRE TRIGGERED: Step budget ({self.context.max_step_limit}) exceeded!"
            )
            self.context.state_trajectory.append(AgentPhase.TERMINATED)
            return AgentPhase.TERMINATED

        current = self.context.current_phase

        if current == AgentPhase.STANDBY:
            next_phase = AgentPhase.SENSING
        elif current == AgentPhase.SENSING:
            if perception_data:
                self.context.memory_buffer.append(perception_data)
            next_phase = AgentPhase.REASONING
        elif current == AgentPhase.REASONING:
            next_phase = AgentPhase.TERMINATED if goal_achieved else AgentPhase.DISPATCHING
        elif current == AgentPhase.DISPATCHING:
            next_phase = AgentPhase.AUDITING
        elif current == AgentPhase.AUDITING:
            next_phase = AgentPhase.EVALUATING
        elif current == AgentPhase.EVALUATING:
            next_phase = AgentPhase.TERMINATED if goal_achieved else AgentPhase.REASONING
        else:
            next_phase = AgentPhase.TERMINATED

        self.context.current_phase = next_phase
        self.context.state_trajectory.append(next_phase)

        if next_phase == AgentPhase.TERMINATED:
            self.context.is_halted = True

        return next_phase


if __name__ == "__main__":
    print("[Winograd - Systems Architect] Autonomous State Machine Verification:")
    fsm = AutonomousNavigatorStateMachine(max_steps=10)
    print(f"Initial Phase: {fsm.context.current_phase.name}")

    for step_num in range(1, 15):
        phase = fsm.step(perception_data={"sensor_reading_id": step_num})
        print(f"Step {step_num:02d}: Phase -> {phase.name}")
        if fsm.context.is_halted:
            print(f"Halt confirmed: {fsm.context.forced_termination_reason or 'Natural Goal Completion'}")
            break
