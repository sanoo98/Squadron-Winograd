"""
Mission 08: Part 2 - Communications & Protocol Officer
Module: reflexion_surgeon.py
Cadet: Muhammad Usman Maratib (Communications & Protocol Officer)
Squadron: Winograd
Sector: SEC-08-CYG (Cygnus X-1 Accretion Corona)

Description:
    3-Actor Reflexion Loop (Actor -> Evaluator -> Self-Reflection) with AST traceback surgery,
    sliding episodic memory buffer (Omega = 3), and SHA-256 patch deduplication.
"""

from __future__ import annotations
import re
import hashlib
from typing import List, Dict, Any, Tuple, Callable


class ReflexionSurgeon:
    """Manages traceback diagnostic extraction and verbal self-reflection repair loops."""

    def __init__(self, memory_window: int = 3) -> None:
        self.memory_window = memory_window  # Omega = 3
        self.episodic_memory: List[str] = []
        self.seen_patch_hashes: List[str] = []

    @staticmethod
    def parse_traceback(stderr_text: str) -> Dict[str, Any]:
        """Extracts file, line_number, exception_type, and fault_summary from stack traces."""
        diag = {
            "file": "unknown",
            "line_number": -1,
            "exception_type": "UnknownException",
            "fault_summary": "Unspecified runtime fault",
        }

        # Match: File "...", line X
        matches = re.findall(r'File\s+"([^"]+)",\s+line\s+(\d+)', stderr_text)
        if matches:
            diag["file"] = matches[-1][0]
            diag["line_number"] = int(matches[-1][1])

        # Match exception class and description
        exc_match = re.search(r"([A-Za-z_][A-Za-z0-9_]*Error|[A-Za-z_][A-Za-z0-9_]*Exception):\s*(.*)", stderr_text)
        if exc_match:
            diag["exception_type"] = exc_match.group(1).strip()
            diag["fault_summary"] = exc_match.group(2).strip()
        else:
            lines = [l.strip() for l in stderr_text.strip().splitlines() if l.strip()]
            if lines:
                diag["fault_summary"] = lines[-1]

        return diag

    def generate_verbal_reflection(self, diag: Dict[str, Any], failed_code: str) -> str:
        """
        Synthesizes a structured verbal reflection r_k and updates bounded episodic buffer:
            M_ep^(k+1) = Tail_Omega(M_ep^(k) union {r_k}), Omega = 3
        """
        exc = diag["exception_type"]
        line = diag["line_number"]
        summary = diag["fault_summary"]

        trial_num = len(self.episodic_memory) + 1
        reflection = (
            f"Reflection [Trial {trial_num}]: Fault {exc} observed at line {line} ('{summary}'). "
            f"Corrective Rule: Add explicit validation to prevent {exc}."
        )

        self.episodic_memory.append(reflection)
        if len(self.episodic_memory) > self.memory_window:
            self.episodic_memory = self.episodic_memory[-self.memory_window:]

        return reflection

    def is_duplicate_patch(self, candidate_code: str) -> bool:
        """Computes SHA-256 hash of whitespace-normalized code to detect cyclic patches."""
        norm_code = "".join(candidate_code.split())
        code_hash = hashlib.sha256(norm_code.encode("utf-8")).hexdigest()
        if code_hash in self.seen_patch_hashes:
            return True
        self.seen_patch_hashes.append(code_hash)
        return False

    def run_repair_loop(
        self,
        initial_code: str,
        test_fn: Callable[[str], Tuple[bool, str]],
        patch_generator: Callable[[str, List[str]], str],
        max_trials: int = 4,
    ) -> Dict[str, Any]:
        """Executes the 3-Actor Reflexion loop until tests pass or max_trials reached."""
        current_code = initial_code
        self.seen_patch_hashes.clear()
        self.episodic_memory.clear()

        for trial in range(1, max_trials + 1):
            if self.is_duplicate_patch(current_code) and trial > 1:
                return {
                    "success": False,
                    "final_code": current_code,
                    "trials_completed": trial,
                    "error": "Cyclic patch detected: SHA-256 collision in candidate code.",
                    "reflections": list(self.episodic_memory),
                }

            passed, stderr = test_fn(current_code)
            if passed:
                return {
                    "success": True,
                    "final_code": current_code,
                    "trials_completed": trial,
                    "error": None,
                    "reflections": list(self.episodic_memory),
                }

            diag = self.parse_traceback(stderr)
            reflection = self.generate_verbal_reflection(diag, current_code)
            current_code = patch_generator(current_code, list(self.episodic_memory))

        return {
            "success": False,
            "final_code": current_code,
            "trials_completed": max_trials,
            "error": "Max trials exceeded without passing unit test suite.",
            "reflections": list(self.episodic_memory),
        }


if __name__ == "__main__":
    print("[Winograd - Protocol Officer] Standalone Reflexion Surgeon Test:")
    surgeon = ReflexionSurgeon(memory_window=3)
    sample_trace = """
    Traceback (most recent call last):
      File "flux_synthesizer.py", line 55, in compute_attenuation
        flux_val = raw_signal / scale_factor
    ZeroDivisionError: division by zero
    """
    d = surgeon.parse_traceback(sample_trace)
    print(f"Extracted Diagnostic: {d['exception_type']} at line {d['line_number']} in {d['file']}")
    r = surgeon.generate_verbal_reflection(d, "sample_code")
    print(f"Verbal Reflection: {r}")
