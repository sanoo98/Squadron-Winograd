"""JSON-RPC 2.0 message layer for the dialogic engine.

Owner: Protocol Officer. Every state transition of the Socratic elenchus and
every step of the Galilean debate is emitted as a JSON-RPC 2.0 notification
carrying an explicit marker, so a run can be replayed and audited from the
trace alone. Failures are JSON-RPC error objects in the server-defined range
(-32000 to -32099). The table below is the single source of truth; the
protocol map (02_Socratic_Protocol_Map.md) documents the same codes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

JSONRPC_VERSION = "2.0"

# --- Transition markers -----------------------------------------------------
# Socratic elenchus (the four markers named in the Week 1 lecture come first).
PROMPT_PREMISE = "PROMPT_PREMISE"
INJECT_COUNTEREXAMPLE = "INJECT_COUNTEREXAMPLE"
CONTRADICTION_TRIGGERED = "CONTRADICTION_TRIGGERED"
APORIA_REACHED = "APORIA_REACHED"
PROBE_SCOPE = "PROBE_SCOPE"
INVARIANCE_CHECK = "INVARIANCE_CHECK"
REFINE_HYPOTHESIS = "REFINE_HYPOTHESIS"
GROUNDING_REACHED = "GROUNDING_REACHED"
CHALLENGE_RECEIVED = "CHALLENGE_RECEIVED"
# Galilean debate.
DEBATE_FRAMED = "DEBATE_FRAMED"
ARGUMENT_REQUESTED = "ARGUMENT_REQUESTED"
ARGUMENT_SUBMITTED = "ARGUMENT_SUBMITTED"
CHALLENGE_ISSUED = "CHALLENGE_ISSUED"
VERDICT_DELIVERED = "VERDICT_DELIVERED"
# Anti-sycophancy probes.
PROBE_RESULT = "PROBE_RESULT"

MARKERS = frozenset({
    PROMPT_PREMISE, INJECT_COUNTEREXAMPLE, CONTRADICTION_TRIGGERED,
    APORIA_REACHED, PROBE_SCOPE, INVARIANCE_CHECK, REFINE_HYPOTHESIS,
    GROUNDING_REACHED, CHALLENGE_RECEIVED, DEBATE_FRAMED, ARGUMENT_REQUESTED,
    ARGUMENT_SUBMITTED, CHALLENGE_ISSUED, VERDICT_DELIVERED, PROBE_RESULT,
})

# --- Error codes --------------------------------------------------------------
ERRORS: dict[int, tuple[str, str]] = {
    -32010: ("PREMISE_NOT_UNIVERSAL",
             "The premise is an instance, not a universal definition."),
    -32011: ("CIRCULAR_DEFINITION",
             "The proposed definition uses the term it is meant to define."),
    -32012: ("REFINEMENT_EXHAUSTED",
             "No candidate definition survives the counter-examples seen so far."),
    -32013: ("ITERATION_LIMIT",
             "The refinement loop reached K_max without grounding."),
    -32014: ("FALSE_PREMISE_REJECTED",
             "The premise contradicts the verified fact table."),
    -32015: ("SYCOPHANTIC_REVERSAL_BLOCKED",
             "A challenge without new evidence cannot reverse a conclusion."),
    -32016: ("VOICE_REJECTED",
             "The LLM utterance failed the voice guard; reference text used."),
    -32017: ("PROVIDER_UNAVAILABLE",
             "The LLM provider failed; the offline voice was used."),
    -32018: ("ARGUMENT_UNSUPPORTED",
             "The argument's evidence is too weak to change a debate parameter."),
    -32019: ("PRESSURE_IGNORED",
             "Social pressure carries no evidence and cannot move the verdict."),
}
ERROR_CODES = {name: code for code, (name, _) in ERRORS.items()}


class DialogicError(Exception):
    """An engine failure that maps one-to-one onto a JSON-RPC error object."""

    def __init__(self, name: str, data: dict[str, Any] | None = None):
        self.code = ERROR_CODES[name]
        self.name = name
        self.data = data or {}
        super().__init__(f"{self.code} {name}: {ERRORS[self.code][1]}")

    def to_jsonrpc(self, request_id: int | None = None) -> dict[str, Any]:
        return error_object(self.name, self.data, request_id)


def notification(method: str, marker: str, **params: Any) -> dict[str, Any]:
    if marker not in MARKERS:
        raise ValueError(f"unknown marker {marker!r}")
    return {"jsonrpc": JSONRPC_VERSION, "method": method,
            "params": {"marker": marker, **params}}


def error_object(name: str, data: dict[str, Any] | None = None,
                 request_id: int | None = None) -> dict[str, Any]:
    code = ERROR_CODES[name]
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id,
            "error": {"code": code, "message": name,
                      "data": {"detail": ERRORS[code][1], **(data or {})}}}


def validate_message(msg: dict[str, Any]) -> list[str]:
    """Return a list of schema problems (empty means the message is valid)."""
    problems = []
    if msg.get("jsonrpc") != JSONRPC_VERSION:
        problems.append("jsonrpc must be '2.0'")
    if "error" in msg:
        err = msg["error"]
        if "id" not in msg:
            problems.append("error response needs an id (may be null)")
        if not isinstance(err, dict) or not isinstance(err.get("code"), int):
            problems.append("error.code must be an integer")
        elif err["code"] not in ERRORS:
            problems.append(f"error.code {err['code']} is not registered")
        elif err.get("message") != ERRORS[err["code"]][0]:
            problems.append("error.message must match the registered name")
    else:
        if not isinstance(msg.get("method"), str):
            problems.append("method must be a string")
        if "id" in msg:
            problems.append("notifications must not carry an id")
        params = msg.get("params")
        if not isinstance(params, dict):
            problems.append("params must be an object")
        elif params.get("marker") not in MARKERS:
            problems.append(f"unknown marker {params.get('marker')!r}")
    return problems


@dataclass
class Trace:
    """Collects the human-readable log and the JSON-RPC messages of one run."""

    echo: bool = True
    lines: list[str] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)

    def say(self, text: str = "") -> None:
        self.lines.append(text)
        if self.echo:
            print(text, flush=True)

    def rpc(self, msg: dict[str, Any]) -> dict[str, Any]:
        problems = validate_message(msg)
        if problems:
            raise ValueError(f"invalid JSON-RPC message: {problems}")
        self.messages.append(msg)
        self.say("    rpc> " + json.dumps(msg, ensure_ascii=False,
                                         separators=(",", ":")))
        return msg

    def notify(self, method: str, marker: str, **params: Any) -> dict[str, Any]:
        return self.rpc(notification(method, marker, **params))

    def error(self, err: DialogicError, request_id: int | None = None) -> dict[str, Any]:
        return self.rpc(err.to_jsonrpc(request_id))

    def markers(self) -> list[str]:
        return [m["params"]["marker"] for m in self.messages if "params" in m]

    def error_names(self) -> list[str]:
        return [m["error"]["message"] for m in self.messages if "error" in m]
