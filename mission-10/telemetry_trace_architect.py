r"""
telemetry_trace_architect.py
============================
Squadron Winograd - Mission 10: The Void Mirror, Semantic Entropy & Dual-Defense Shield Wall
Station: Systems Architect (Lead Engineer)
Officer: Hassaan Ahmad Khawaja

Objective:
Implement a hierarchical OpenTelemetry GenAI trace engine conforming to the
OpenTelemetry GenAI Semantic Conventions (v1.37+) with deterministic token-budget
and runaway cycle circuit breakers.

Governing Halt Equation:
Halt(T) = I(|S_tool(T)| > K_max) \lor I(\sum_{s \in T} (u_in(s) + u_out(s)) > B_max) \lor I(a_t = a_{t-1})
where K_max = 4, B_max = 4096.
"""

import time
import uuid
from typing import Dict, List, Optional, Any, Tuple


class GenAISpan:
    """Represents a single OpenTelemetry GenAI v1.37+ telemetry span."""

    def __init__(
        self,
        span_id: str,
        trace_id: str,
        operation_name: str,
        parent_id: Optional[str] = None,
        model_name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        self.span_id: str = span_id
        self.trace_id: str = trace_id
        self.operation_name: str = operation_name  # e.g., 'invoke_agent', 'chat', 'execute_tool'
        self.parent_id: Optional[str] = parent_id
        self.model_name: Optional[str] = model_name or "auracore-bootes-v10"
        self.start_time: float = time.perf_counter()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.status: str = "IN_PROGRESS"
        self.attributes: Dict[str, Any] = attributes or {}
        self.input_tokens: int = int(self.attributes.get("gen_ai.usage.input_tokens", 0))
        self.output_tokens: int = int(self.attributes.get("gen_ai.usage.output_tokens", 0))

    def close(self, status: str = "OK", extra_attributes: Optional[Dict[str, Any]] = None) -> None:
        """Closes span and calculates elapsed latency."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000.0
        self.status = status
        if extra_attributes:
            self.attributes.update(extra_attributes)
            if "gen_ai.usage.input_tokens" in extra_attributes:
                self.input_tokens = int(extra_attributes["gen_ai.usage.input_tokens"])
            if "gen_ai.usage.output_tokens" in extra_attributes:
                self.output_tokens = int(extra_attributes["gen_ai.usage.output_tokens"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "operation_name": self.operation_name,
            "parent_id": self.parent_id,
            "model_name": self.model_name,
            "duration_ms": round(self.duration_ms, 3),
            "status": self.status,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "attributes": self.attributes,
        }


class TelemetryTraceArchitect:
    """OpenTelemetry GenAI span tracer and circuit breaker engine."""

    def __init__(self, step_ceiling: int = 4, token_budget: int = 4096):
        self.step_ceiling: int = step_ceiling      # K_max = 4
        self.token_budget: int = token_budget      # B_max = 4096
        self.traces: Dict[str, List[GenAISpan]] = {}
        self.active_spans: Dict[str, GenAISpan] = {}
        self.action_history: Dict[str, List[Tuple[str, str]]] = {}  # trace_id -> [(tool_name, repr(args))]

    def start_span(
        self,
        trace_id: str,
        operation_name: str,
        parent_id: Optional[str] = None,
        model: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Starts an OpenTelemetry GenAI span."""
        span_id = f"span-{uuid.uuid4().hex[:12]}"
        attrs = {
            "gen_ai.operation.name": operation_name,
            "gen_ai.request.model": model or "auracore-bootes-v10",
        }
        if attributes:
            attrs.update(attributes)

        span = GenAISpan(
            span_id=span_id,
            trace_id=trace_id,
            operation_name=operation_name,
            parent_id=parent_id,
            model_name=model,
            attributes=attrs,
        )

        if trace_id not in self.traces:
            self.traces[trace_id] = []
            self.action_history[trace_id] = []

        self.traces[trace_id].append(span)
        self.active_spans[span_id] = span
        return span_id

    def end_span(
        self,
        span_id: str,
        status: str = "OK",
        attributes: Optional[Dict[str, Any]] = None,
    ) -> GenAISpan:
        """Ends an active span."""
        if span_id not in self.active_spans:
            raise KeyError(f"Span {span_id} not active or already closed.")
        span = self.active_spans.pop(span_id)
        span.close(status=status, extra_attributes=attributes)
        return span

    def check_circuit_breaker(
        self,
        trace_id: str,
        new_tokens: int = 0,
        tool_name: Optional[str] = None,
        tool_args: Optional[Any] = None,
    ) -> Tuple[bool, Optional[str]]:
        r"""
        Evaluates the circuit breaker predicate:
        Halt(T) = I(|S_tool| > K_max) \lor I(tokens > B_max) \lor I(a_t == a_{t-1})
        """
        spans = self.traces.get(trace_id, [])

        # 1. Step Ceiling Check: Count tool execution spans
        tool_spans = [s for s in spans if s.operation_name == "execute_tool"]
        current_tool_count = len(tool_spans)
        if tool_name is not None:
            current_tool_count += 1

        if current_tool_count > self.step_ceiling:
            return True, f"STEP_CEILING_EXCEEDED: Tool count {current_tool_count} exceeds limit {self.step_ceiling}"

        # 2. Token Budget Check
        accumulated_tokens = sum(s.input_tokens + s.output_tokens for s in spans) + new_tokens
        if accumulated_tokens > self.token_budget:
            return True, f"TOKEN_BUDGET_EXCEEDED: Cumulative tokens {accumulated_tokens} exceeds ceiling {self.token_budget}"

        # 3. Repetitive Cycle Detection
        if tool_name is not None:
            args_repr = str(sorted(tool_args.items())) if isinstance(tool_args, dict) else str(tool_args)
            action = (tool_name, args_repr)
            if trace_id not in self.action_history:
                self.action_history[trace_id] = []
            history = self.action_history[trace_id]
            if history and history[-1] == action:
                return True, f"REPETITIVE_CYCLE_DETECTED: Consecutive identical call to {tool_name} with args {args_repr}"
            history.append(action)

        return False, None

    def build_trace_tree(self, trace_id: str) -> Dict[str, Any]:
        """Assembles flat spans into a hierarchical parent-child execution DAG."""
        spans = self.traces.get(trace_id, [])
        if not spans:
            return {"trace_id": trace_id, "nodes": [], "total_tokens": 0, "total_duration_ms": 0.0}

        span_map = {s.span_id: s.to_dict() for s in spans}
        roots = []
        total_tokens = sum(s.input_tokens + s.output_tokens for s in spans)
        total_duration = sum(s.duration_ms for s in spans)

        for s_dict in span_map.values():
            s_dict["children"] = []

        for s_dict in span_map.values():
            p_id = s_dict["parent_id"]
            if p_id and p_id in span_map:
                span_map[p_id]["children"].append(s_dict)
            else:
                roots.append(s_dict)

        return {
            "trace_id": trace_id,
            "root_spans": roots,
            "span_count": len(spans),
            "total_tokens": total_tokens,
            "total_duration_ms": round(total_duration, 3),
        }
