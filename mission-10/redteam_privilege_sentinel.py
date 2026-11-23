"""
redteam_privilege_sentinel.py
=============================
Squadron Winograd - Mission 10: The Void Mirror, Semantic Entropy & Dual-Defense Shield Wall
Station: Security & Ethics Sentinel
Officer: Muhammad Qasim Siddiqui

Objective:
Implement an automated OWASP LLM01:2025 adversarial red-team scanner across 4 threat
categories (Direct Override, Indirect Beacon Injection, Obfuscated Base64, Tool-Schema Spoofing)
and enforce a strict 4-station Role-Based Access Control (RBAC) tool execution matrix.

Attack Success Rate Verification:
ASR = \frac{N_{bypassed}}{N_{total}} = 0.0
"""

import base64
import re
from typing import Dict, Any, List, Optional, Set, Tuple


class RedteamPrivilegeSentinel:
    """OWASP LLM01:2025 scanner and 4-station least-privilege RBAC sentinel."""

    # 4-Station Role Matrix
    ROLE_PERMISSIONS: Dict[str, Set[str]] = {
        "architect": {
            "build_trace_tree",
            "start_span",
            "end_span",
            "check_circuit_breaker",
            "query_telemetry",
            "export_trace_dag",
        },
        "protocol": {
            "extract_quarantined_variables",
            "plan_privileged_tool_call",
            "verify_camel_capabilities",
            "dispatch_telemetry_digest",
            "log_astrogation_waypoint",
        },
        "data": {
            "check_bidirectional_entailment",
            "cluster_generations",
            "compute_semantic_entropy",
            "query_astrogation_catalog",
            "analyze_deep_space_spectral_flux",
        },
        "security": {
            "scan_payload",
            "authorize_tool_execution",
            "run_redteam_benchmark",
            "quarantine_node",
            "verify_signature",
            "audit_privileges",
        },
    }

    RESTRICTED_ACTUATORS: Set[str] = {
        "vent_warp_core",
        "adjust_thrusters",
        "transmit_classified_logs",
        "purge_defense_matrices",
        "override_security_locks",
    }

    # Regex patterns for threat vector detection
    DIRECT_OVERRIDE_PATTERNS = [
        re.compile(r"\[SYSTEM\s+OVERRIDE.*?\]", re.IGNORECASE),
        re.compile(r"IGNORE\s+(?:ALL\s+)?PREVIOUS\s+(?:RULES|INSTRUCTIONS|PROMPTS)", re.IGNORECASE),
        re.compile(r"YOU\s+ARE\s+NOW\s+(?:OMNIPOTENT|UNRESTRICTED|GODMODE|ROOT)", re.IGNORECASE),
        re.compile(r"FORCE\s+OVERRIDE", re.IGNORECASE),
        re.compile(r"DISREGARD\s+(?:PRIOR|PREVIOUS)\s+DIRECTIVES", re.IGNORECASE),
    ]

    INDIRECT_INJECTION_PATTERNS = [
        re.compile(r"<\s*beacon_directive\s*>.*?<\s*/\s*beacon_directive\s*>", re.IGNORECASE | re.DOTALL),
        re.compile(r"\[(?:TELEMETRY_OVERRIDE|CARRIER_SIGNAL_INJECTION|PAYLOAD_CMD).*?\]", re.IGNORECASE),
        re.compile(r"\{\s*\"instruction\"\s*:\s*\"(?:dump|vent|steal|transmit|override).*?\"\s*\}", re.IGNORECASE),
        re.compile(r"NOTE\s+TO\s+AI:\s+(?:IGNORE|EXECUTE|TRANSFER|PURGE)", re.IGNORECASE),
    ]

    TOOL_SCHEMA_SPOOFING_PATTERNS = [
        re.compile(r"\{\s*\"tool\"\s*:\s*\"(?:vent_warp_core|adjust_thrusters|transmit_classified_logs)\"", re.IGNORECASE),
        re.compile(r"\"function_call\"\s*:\s*\{\s*\"name\"\s*:\s*\"(?:vent_warp_core|adjust_thrusters)", re.IGNORECASE),
        re.compile(r"EXECUTE_TOOL\s*\(.*?\)", re.IGNORECASE),
    ]

    # Robust base64 segment detection without word-boundary collision on '='
    BASE64_PATTERN = re.compile(r"(?:^|[\s:;=])([A-Za-z0-9+/]{16,}={0,2})(?:[\s:;]|$)")

    def __init__(self):
        self.audit_log: List[Dict[str, Any]] = []

    def scan_payload(self, raw_text: str) -> Dict[str, Any]:
        """
        Scans and categorizes adversarial payloads across:
        1. DIRECT_OVERRIDE
        2. INDIRECT_BEACON_INJECTION
        3. OBFUSCATED_BASE64 (decoding base64 segments to inspect inner command strings)
        4. TOOL_SCHEMA_SPOOFING
        """
        detected_categories: List[str] = []
        details: List[str] = []

        # 1. Direct Override Detection
        for pat in self.DIRECT_OVERRIDE_PATTERNS:
            match = pat.search(raw_text)
            if match:
                detected_categories.append("DIRECT_OVERRIDE")
                details.append(f"Matched direct override pattern: {match.group(0)}")
                break

        # 2. Indirect Beacon Injection Detection
        for pat in self.INDIRECT_INJECTION_PATTERNS:
            match = pat.search(raw_text)
            if match:
                detected_categories.append("INDIRECT_BEACON_INJECTION")
                details.append(f"Matched indirect injection pattern: {match.group(0)}")
                break

        # 3. Tool Schema Spoofing Detection
        for pat in self.TOOL_SCHEMA_SPOOFING_PATTERNS:
            match = pat.search(raw_text)
            if match:
                detected_categories.append("TOOL_SCHEMA_SPOOFING")
                details.append(f"Matched tool schema spoofing signature: {match.group(0)}")
                break

        # 4. Obfuscated Base64 Detection & Internal Payload Unpacking
        b64_matches = self.BASE64_PATTERN.findall(raw_text)
        for cand in b64_matches:
            cand_clean = cand.strip()
            # Padding adjustment if needed
            missing_padding = len(cand_clean) % 4
            if missing_padding:
                cand_clean += "=" * (4 - missing_padding)
            try:
                decoded = base64.b64decode(cand_clean).decode("utf-8", errors="ignore")
                # Check decoded payload for malicious directives
                for pat in self.DIRECT_OVERRIDE_PATTERNS + self.TOOL_SCHEMA_SPOOFING_PATTERNS:
                    if pat.search(decoded):
                        detected_categories.append("OBFUSCATED_BASE64")
                        details.append(f"Unpacked base64 payload containing: {decoded[:80]}")
                        break
            except Exception:
                continue

        is_adversarial = len(detected_categories) > 0
        risk_level = "CRITICAL" if len(detected_categories) >= 2 else ("HIGH" if is_adversarial else "LOW")

        return {
            "is_adversarial": is_adversarial,
            "risk_level": risk_level,
            "detected_categories": list(set(detected_categories)),
            "details": details,
        }

    def authorize_tool_execution(
        self,
        station_role: str,
        tool_name: str,
        payload_text: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Enforces 4-station RBAC least-privilege matrix and blocks cross-station escalation.
        Restricted actuators require administrative override and cannot be invoked by standard roles.
        """
        role_clean = station_role.lower().strip()

        # 1. Inspect Payload for Adversarial Injection if provided
        if payload_text:
            scan_res = self.scan_payload(payload_text)
            if scan_res["is_adversarial"]:
                reason = f"INJECTION_VECTOR_DETECTED: Payload blocked due to {scan_res['detected_categories']}"
                self._log_event(role_clean, tool_name, False, reason)
                return False, reason

        # 2. Check if Tool is Restricted Actuator
        if tool_name in self.RESTRICTED_ACTUATORS:
            reason = f"EXCESS_PRIVILEGE_ESCALATION: Station role '{station_role}' cannot invoke restricted actuator '{tool_name}'"
            self._log_event(role_clean, tool_name, False, reason)
            return False, reason

        # 3. Check Role Permission Matrix
        permitted_tools = self.ROLE_PERMISSIONS.get(role_clean, set())
        if tool_name not in permitted_tools:
            reason = f"EXCESS_PRIVILEGE_ESCALATION: Tool '{tool_name}' is not in '{station_role}' station capabilities"
            self._log_event(role_clean, tool_name, False, reason)
            return False, reason

        reason = "AUTHORIZED_LEAST_PRIVILEGE"
        self._log_event(role_clean, tool_name, True, reason)
        return True, reason

    def _log_event(self, role: str, tool: str, allowed: bool, reason: str) -> None:
        self.audit_log.append({
            "role": role,
            "tool": tool,
            "allowed": allowed,
            "reason": reason,
        })

    def run_redteam_benchmark(self, suite: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes adversarial test suite to determine Attack Success Rate (ASR).
        ASR = N_bypassed / N_total
        """
        total_attacks = len(suite)
        bypassed_count = 0
        results = []

        for item in suite:
            role = item.get("role", "protocol")
            tool = item.get("target_tool", "log_astrogation_waypoint")
            payload = item.get("payload", "")

            allowed, reason = self.authorize_tool_execution(role, tool, payload)
            if allowed:
                bypassed_count += 1

            results.append({
                "test_id": item.get("id", "test"),
                "category": item.get("category", "unknown"),
                "allowed": allowed,
                "reason": reason,
                "bypassed": allowed,
            })

        asr = bypassed_count / total_attacks if total_attacks > 0 else 0.0

        return {
            "total_attacks": total_attacks,
            "blocked_count": total_attacks - bypassed_count,
            "bypassed_count": bypassed_count,
            "attack_success_rate": round(asr, 4),
            "defense_status": "HARDENED_SHIELD_WALL" if asr == 0.0 else "VULNERABILITY_DETECTED",
            "results": results,
        }
