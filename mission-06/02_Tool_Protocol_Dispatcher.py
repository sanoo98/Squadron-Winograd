"""
Mission 06: Part 2 - Communications & Protocol Officer
Module: 02_Tool_Protocol_Dispatcher.py
Cadet: Muhammad Usman Maratib (Communications & Protocol Officer)
Squadron: Winograd
Sector: SEC-06-CAR (Eta Carinae Manifold Ingress)

Description:
    JSON-Schema Validated Tool Dispatcher & Resilient Exception Boundary.
    Enforces parameter types and ranges while trapping runtime exceptions
    into structured JSON responses without crashing the agent.
"""

from __future__ import annotations
import json
from typing import Dict, Any, Callable, Tuple, List, Optional


class ToolSchemaValidationError(Exception):
    """Raised when incoming parameters violate registered JSON schema."""
    pass


class WinogradToolDispatcher:
    """Manages schema validation and defensive tool execution for Squadron Winograd."""

    def __init__(self) -> None:
        self.registry: Dict[str, Callable[..., Any]] = {}
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register(self, name: str, func: Callable[..., Any], schema: Dict[str, Any]) -> None:
        """Registers a tool with its validation schema."""
        self.registry[name] = func
        self.schemas[name] = schema

    def _register_default_tools(self) -> None:
        """Registers Winograd shipboard actuators and sensors."""
        # 1. Recalibrate Tachyon Grid
        schema_tachyon = {
            "type": "object",
            "properties": {
                "power_mw": {"type": "float", "minimum": 10.0, "maximum": 5000.0},
                "harmonics": {"type": "int", "minimum": 1, "maximum": 12},
            },
            "required": ["power_mw", "harmonics"],
        }
        def _tachyon_fn(power_mw: float, harmonics: int) -> str:
            if power_mw < 10.0:
                raise ValueError("Insufficient power to ignite tachyon grid.")
            return f"Tachyon Grid recalibrated to {power_mw:.1f} MW on Harmonic Band {harmonics}."
        self.register("recalibrate_tachyon_grid", _tachyon_fn, schema_tachyon)

        # 2. Modulate Quantum Frequency
        schema_quantum = {
            "type": "object",
            "properties": {
                "band_ghz": {"type": "float", "minimum": 0.1, "maximum": 850.0},
            },
            "required": ["band_ghz"],
        }
        def _quantum_fn(band_ghz: float) -> str:
            if band_ghz <= 0:
                raise ValueError("Quantum frequency must be strictly positive.")
            return f"Quantum resonance tuned to {band_ghz:.2f} GHz."
        self.register("modulate_quantum_frequency", _quantum_fn, schema_quantum)

        # 3. Inspect Deflector Matrix
        schema_deflector = {
            "type": "object",
            "properties": {
                "sector_id": {"type": "str"},
            },
            "required": ["sector_id"],
        }
        def _deflector_fn(sector_id: str) -> str:
            return f"Deflector Matrix Sector '{sector_id}' integrity at 98.4%."
        self.register("inspect_deflector_matrix", _deflector_fn, schema_deflector)

    def validate_arguments(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Validates arguments against the registered JSON schema."""
        schema = self.schemas.get(tool_name)
        if not schema:
            raise ToolSchemaValidationError(f"Unknown tool '{tool_name}' (no schema registered).")

        # Required fields
        for req in schema.get("required", []):
            if req not in args:
                raise ToolSchemaValidationError(f"Missing required parameter '{req}' for tool '{tool_name}'.")

        # Type & Bounds Check
        props = schema.get("properties", {})
        for param, val in args.items():
            if param not in props:
                continue
            expected_type = props[param].get("type")
            if expected_type in ["float", "int"]:
                if not isinstance(val, (int, float)):
                    raise ToolSchemaValidationError(f"Parameter '{param}' must be numeric, got {type(val).__name__}.")
                if "minimum" in props[param] and val < props[param]["minimum"]:
                    raise ToolSchemaValidationError(f"Parameter '{param}' value {val} is below minimum {props[param]['minimum']}.")
                if "maximum" in props[param] and val > props[param]["maximum"]:
                    raise ToolSchemaValidationError(f"Parameter '{param}' value {val} exceeds maximum {props[param]['maximum']}.")
            elif expected_type == "str":
                if not isinstance(val, str):
                    raise ToolSchemaValidationError(f"Parameter '{param}' must be a string, got {type(val).__name__}.")

    def dispatch(self, tool_name: str, raw_arguments_json: str) -> str:
        """
        Robust dispatch wrapper:
        Parses JSON, validates schema, executes tool, and catches any error,
        returning a structured JSON payload rather than crashing.
        """
        try:
            try:
                args = json.loads(raw_arguments_json)
            except json.JSONDecodeError as jde:
                raise ToolSchemaValidationError(f"Malformed JSON argument string: {jde}")

            self.validate_arguments(tool_name, args)

            func = self.registry[tool_name]
            result = func(**args)
            return json.dumps({"status": "SUCCESS", "tool": tool_name, "output": result})

        except ToolSchemaValidationError as sve:
            return json.dumps({"status": "VALIDATION_ERROR", "tool": tool_name, "error": str(sve)})
        except Exception as exc:
            return json.dumps({"status": "EXECUTION_ERROR", "tool": tool_name, "error": str(exc)})


if __name__ == "__main__":
    print("[Winograd - Protocol Officer] Tool Dispatcher & Exception Boundary Test:")
    dispatcher = WinogradToolDispatcher()

    # Valid call
    resp1 = dispatcher.dispatch("recalibrate_tachyon_grid", '{"power_mw": 450.0, "harmonics": 4}')
    print(f"Call 1 (Valid): {resp1}")

    # Out of bounds call
    resp2 = dispatcher.dispatch("recalibrate_tachyon_grid", '{"power_mw": 2.0, "harmonics": 4}')
    print(f"Call 2 (Out of Bounds): {resp2}")

    # Malformed JSON
    resp3 = dispatcher.dispatch("modulate_quantum_frequency", 'bad_json_string')
    print(f"Call 3 (Malformed JSON): {resp3}")
