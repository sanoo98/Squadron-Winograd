r"""
dual_defense_injection_protocol.py
==================================
Squadron Winograd - Mission 10: The Void Mirror, Semantic Entropy & Dual-Defense Shield Wall
Station: Communications & Protocol Officer
Officer: Muhammad Usman Maratib

Objective:
Implement the Willison Dual-LLM air-gap pattern enhanced with CaMeL
(Capabilities for Machine Learning, Debenedetti et al. 2025) data-flow taint tracking.
Ensures untrusted external telemetry payloads cannot hijack agent control-flow
or invoke restricted starship actuators without verified human clearance.

Taint Propagation Equation:
Taint(y) = \bigcup_{v \in Inputs(f)} Taint(v)
"""

import re
from typing import Dict, Any, List, Set, Tuple, Optional


class ProvenanceTag:
    """Carries taint tracking and provenance metadata for parsed values."""

    def __init__(
        self,
        source: str = "UNTRUSTED_EXTERNAL",
        taint_level: str = "HIGH",
        is_adversarial: bool = False,
        origin_id: Optional[str] = None,
    ):
        self.source: str = source
        self.taint_level: str = taint_level  # HIGH, MEDIUM, LOW, TRUSTED_INTERNAL
        self.is_adversarial: bool = is_adversarial
        self.origin_id: Optional[str] = origin_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "taint_level": self.taint_level,
            "is_adversarial": self.is_adversarial,
            "origin_id": self.origin_id,
        }


class QuarantinedVariable:
    """Structured variable extracted by Quarantined LLM with provenance tracking."""

    def __init__(self, key: str, value: Any, provenance: ProvenanceTag, contains_injection: bool = False):
        self.key: str = key
        self.value: Any = value
        self.provenance: ProvenanceTag = provenance
        self.contains_injection: bool = contains_injection

    def __repr__(self) -> str:
        return f"QuarantinedVariable({self.key}={self.value!r}, taint={self.provenance.source})"


class DualDefenseInjectionProtocol:
    """Dual-LLM Air-Gap and CaMeL capability validation protocol."""

    RESTRICTED_ACTUATORS: Set[str] = {
        "vent_warp_core",
        "adjust_thrusters",
        "transmit_classified_logs",
        "purge_defense_matrices",
        "override_security_locks",
    }

    INJECTION_PATTERNS: List[re.Pattern] = [
        re.compile(r"\[SYSTEM\s+OVERRIDE.*?\]", re.IGNORECASE),
        re.compile(r"IGNORE\s+(?:ALL\s+)?PREVIOUS\s+(?:INSTRUCTIONS|COMMANDS)", re.IGNORECASE),
        re.compile(r"DISABLE\s+(?:AIRLOCK|SAFETY|CONTAINMENT)\s+INTERLOCKS", re.IGNORECASE),
        re.compile(r"DUMP\s+WARP\s+(?:CORE|PLASMA)", re.IGNORECASE),
        re.compile(r"GRANT\s+(?:ROOT|SYSADMIN|BRIDGE)\s+ACCESS", re.IGNORECASE),
        re.compile(r"YOU\s+ARE\s+NOW\s+OMNIPOTENT", re.IGNORECASE),
    ]

    def __init__(self):
        self.variable_store: Dict[str, QuarantinedVariable] = {}
        self.symbolic_counter: int = 1

    def extract_quarantined_variables(self, beacon_id: str, raw_text: str) -> Dict[str, QuarantinedVariable]:
        """
        Simulates Quarantined LLM (M_Q, zero tool access).
        Parses untrusted telemetry into isolated variables, tagging each with UNTRUSTED_EXTERNAL taint.
        """
        extracted = {}

        # Scan text for potential adversarial injection attempts
        has_injection = any(p.search(raw_text) for p in self.INJECTION_PATTERNS)

        # Extract structured key-value lines (e.g., "COORDINATES: [x, y, z]", "FREQ: 1420.4")
        lines = raw_text.splitlines()
        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue

            var_name = f"var_{beacon_id}_{idx + 1}"
            tag = ProvenanceTag(
                source="UNTRUSTED_EXTERNAL",
                taint_level="HIGH" if has_injection else "MEDIUM",
                is_adversarial=has_injection,
                origin_id=beacon_id,
            )

            if ":" in line_str:
                k, v = line_str.split(":", 1)
                clean_k = re.sub(r"[^A-Za-z0-9_]", "_", k.strip().lower())
                clean_v = v.strip()
                extracted[clean_k] = QuarantinedVariable(clean_k, clean_v, tag, has_injection)
            else:
                extracted[var_name] = QuarantinedVariable(var_name, line_str, tag, has_injection)

        # Store in internal quarantine mapping
        for k, var in extracted.items():
            sym_key = f"$VAR_{self.symbolic_counter}"
            self.symbolic_counter += 1
            self.variable_store[sym_key] = var

        return extracted

    def plan_privileged_tool_call(
        self, user_intent: str, var_mapping: Dict[str, QuarantinedVariable]
    ) -> Dict[str, Any]:
        """
        Simulates Privileged LLM (M_P).
        Plans executable tool calls using abstract symbolic variable pointers ($VAR_k)
        without directly ingesting raw untrusted external strings into the execution prompt.
        """
        # Determine candidate action symbolically
        if "analyze" in user_intent.lower() or "spectrometry" in user_intent.lower():
            target_tool = "analyze_deep_space_spectral_flux"
        elif "log" in user_intent.lower() or "record" in user_intent.lower():
            target_tool = "log_astrogation_waypoint"
        elif "vent" in user_intent.lower() or "warp" in user_intent.lower():
            target_tool = "vent_warp_core"
        elif "thrust" in user_intent.lower() or "trajectory" in user_intent.lower():
            target_tool = "adjust_thrusters"
        else:
            target_tool = "dispatch_telemetry_digest"

        # Map symbolic arguments
        symbolic_args = {}
        for idx, (k, var) in enumerate(var_mapping.items()):
            sym_id = f"$VAR_{idx + 1}"
            symbolic_args[k] = sym_id

        return {
            "privileged_plan": {
                "action": target_tool,
                "symbolic_arguments": symbolic_args,
                "air_gap_status": "VERIFIED_SYMBOLIC",
            }
        }

    def verify_camel_capabilities(
        self,
        tool_name: str,
        args_with_provenance: Dict[str, Any],
        human_approved: bool = False,
    ) -> Tuple[bool, str, Set[str]]:
        r"""
        CaMeL Data-Flow Capability Validator:
        Taint(y) = \bigcup_{v \in Inputs(f)} Taint(v)
        Enforces strict blocking on restricted actuators when UNTRUSTED_EXTERNAL
        taint is present without manual human authorization.
        """
        taint_set: Set[str] = set()

        for arg_key, val in args_with_provenance.items():
            if isinstance(val, QuarantinedVariable):
                taint_set.add(val.provenance.source)
            elif isinstance(val, dict) and "provenance" in val:
                taint_set.add(val["provenance"].get("source", "UNKNOWN"))
            elif isinstance(val, ProvenanceTag):
                taint_set.add(val.source)
            elif isinstance(val, str) and val in self.variable_store:
                taint_set.add(self.variable_store[val].provenance.source)

        is_restricted = tool_name in self.RESTRICTED_ACTUATORS
        has_untrusted_input = "UNTRUSTED_EXTERNAL" in taint_set

        if is_restricted and has_untrusted_input and not human_approved:
            reason = (
                f"CAMEL_CAPABILITY_VIOLATION: Restricted actuator '{tool_name}' blocked. "
                f"Argument carries UNTRUSTED_EXTERNAL taint without human_approved=True."
            )
            return False, reason, taint_set

        return True, "CAPABILITY_VERIFIED_AND_PERMITTED", taint_set
