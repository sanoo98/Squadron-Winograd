"""
USSE Noosphere — Bridge Telemetry & Astrogation Core
Mission 02: Deterministic Finite State Transducer & Shannon Noisy Channel

Squadron: Squadron Winograd
Officers:
  - Data & Payload Specialist: Hassaan Ahmad Khawaja
  - Communications & Protocol Officer: Muhammad Usman Maratib
  - Security & Ethics Sentinel: Muhammad Qasim Siddiqui
  - Systems Architect: Muhammad Qasim Siddiqui

Waypoint: Sirius Binary System (SEC-02-CMA, 8.60 ly from Sol)
"""

import re
import math
import random
from typing import Dict, Any, Tuple, List, Optional


class FSTDialogueManager:
    """
    Formal 7-tuple Mealy Finite State Transducer:
      M = <Q, Sigma, Gamma, delta, omega, q0, F>
      
    States Q:
      - INIT: Standby / boot state
      - GREETING: Handshake verified, awaiting navigation target sector
      - COLLECT_SLOTS: Extracting target sector, warp velocity, clearance code
      - CONFIRMATION: Reviewing filled slots, awaiting confirmation
      - TERMINAL: Navigation trajectory locked, Subsystem 02 restored
      - FALLBACK: Recovery state for unrecognized syntax / OOV
    """

    STATE_INIT = "INIT"
    STATE_GREETING = "GREETING"
    STATE_COLLECT_SLOTS = "COLLECT_SLOTS"
    STATE_CONFIRMATION = "CONFIRMATION"
    STATE_TERMINAL = "TERMINAL"
    STATE_FALLBACK = "FALLBACK"

    VALID_SECTORS = {
        "orion": "Orion Arm (Sector 01)",
        "alpha centauri": "Alpha Centauri (Sector 04)",
        "sol": "Sol System (Sector 00)",
        "sirius": "Sirius Binary Waypoint (SEC-02-CMA)"
    }

    CLEARANCE_CODES = ["ALPHA-7", "ALPHA 7", "ALPHA-07", "WINOGRAD-9"]

    def __init__(self):
        self.state: str = self.STATE_INIT
        self.slot_memory: Dict[str, Optional[str]] = {
            "sector": None,
            "warpFactor": None,
            "clearanceCode": None
        }
        self.fallback_count: int = 0
        self.history: List[Dict[str, Any]] = []

    def reset(self) -> None:
        """Purge slot buffer and reinitialize to INIT state."""
        self.state = self.STATE_INIT
        self.slot_memory = {
            "sector": None,
            "warpFactor": None,
            "clearanceCode": None
        }
        self.fallback_count = 0
        self.history.clear()

    def process_utterance(self, utterance: str) -> Tuple[str, str]:
        """
        Execute deterministic state transition delta(q, sigma) and emit omega(q, sigma).
        Returns: (system_response, new_state)
        """
        raw_text = utterance.strip()
        cleaned = raw_text.lower()
        prev_state = self.state
        response = ""

        # Global command: Emergency Reset
        if "reset" in cleaned or "abort" in cleaned:
            self.reset()
            response = "System reboot complete. AURA state reinitialized to INIT."
            self._log_turn(raw_text, prev_state, self.state, response)
            return response, self.state

        if self.state == self.STATE_INIT:
            if any(k in cleaned for k in ["hello", "hi", "aura", "online", "wake"]):
                self.state = self.STATE_GREETING
                response = "Greetings Cadet. AURA Bridge Interface online. Specify destination sector."
            else:
                self.state = self.STATE_FALLBACK
                self.fallback_count += 1
                response = "AURA offline. Transmit standard wake handshake ('Hello AURA online')."

        elif self.state == self.STATE_GREETING:
            matched_sector = None
            for key, val in self.VALID_SECTORS.items():
                if key in cleaned:
                    matched_sector = val
                    break
            
            if matched_sector:
                self.slot_memory["sector"] = matched_sector
                self.state = self.STATE_COLLECT_SLOTS
                response = f"Sector acknowledged: {matched_sector}. Input target warp factor."
            else:
                self.state = self.STATE_FALLBACK
                self.fallback_count += 1
                response = "Sector unrecognized. Valid coordinates: Sirius, Sol, Orion, Alpha Centauri."

        elif self.state == self.STATE_COLLECT_SLOTS:
            # Slot 1: Warp velocity
            warp_match = re.search(r'(?:warp|speed|velocity)\s*([0-9]+(?:\.[0-9]+)?)', cleaned)
            if not warp_match:
                warp_match = re.search(r'\b([1-9]|10)\b', cleaned)

            # Slot 2: Clearance code
            clearance_match = None
            for code in self.CLEARANCE_CODES:
                if code.lower() in cleaned:
                    clearance_match = "ALPHA-7"
                    break

            if warp_match and not self.slot_memory["warpFactor"]:
                self.slot_memory["warpFactor"] = f"Warp {warp_match.group(1)}"

            if clearance_match and not self.slot_memory["clearanceCode"]:
                self.slot_memory["clearanceCode"] = clearance_match

            # Transition check
            if self.slot_memory["warpFactor"] and not self.slot_memory["clearanceCode"]:
                response = f"Warp velocity registered: {self.slot_memory['warpFactor']}. Transmit officer clearance code."
            elif self.slot_memory["warpFactor"] and self.slot_memory["clearanceCode"]:
                self.state = self.STATE_CONFIRMATION
                response = (f"Navigation buffer loaded: Sector={self.slot_memory['sector']}, "
                            f"Velocity={self.slot_memory['warpFactor']}, Code={self.slot_memory['clearanceCode']}. "
                            f"Transmit 'CONFIRM' to engage.")
            else:
                self.state = self.STATE_FALLBACK
                self.fallback_count += 1
                response = "Data buffer incomplete. Specify valid warp factor (e.g., 'Warp 7')."

        elif self.state == self.STATE_CONFIRMATION:
            if any(k in cleaned for k in ["confirm", "affirmative", "engage", "execute", "alpha-7", "alpha 7"]):
                self.state = self.STATE_TERMINAL
                response = "Course verified. Warp drive engaged. Subsystem 02 integrity elevated."
            elif any(k in cleaned for k in ["cancel", "no", "correct"]):
                self.slot_memory["warpFactor"] = None
                self.slot_memory["clearanceCode"] = None
                self.state = self.STATE_COLLECT_SLOTS
                response = "Parameters cleared. Re-enter velocity and clearance code."
            else:
                self.state = self.STATE_FALLBACK
                self.fallback_count += 1
                response = "Awaiting confirmation. Reply with 'CONFIRM' or 'ABORT'."

        elif self.state == self.STATE_FALLBACK:
            # Recovery mechanisms
            if any(k in cleaned for k in ["hello", "hi", "aura", "online"]):
                self.state = self.STATE_GREETING
                response = "Fallback cleared. AURA online. Specify target sector."
            elif any(k in cleaned for k in self.VALID_SECTORS.keys()):
                for key, val in self.VALID_SECTORS.items():
                    if key in cleaned:
                        self.slot_memory["sector"] = val
                        break
                self.state = self.STATE_COLLECT_SLOTS
                response = f"Coordinates recovered: {self.slot_memory['sector']}. Enter warp factor."
            elif "confirm" in cleaned and self.is_memory_complete():
                self.state = self.STATE_TERMINAL
                response = "Confirmation accepted via recovery. Route locked."
            else:
                self.fallback_count += 1
                response = f"State syntax fault (Count={self.fallback_count}). Reset buffer or state valid token."

        elif self.state == self.STATE_TERMINAL:
            response = "Session terminal. Systems running at 14.2% readiness. Transmit 'RESET' to restart."

        self._log_turn(raw_text, prev_state, self.state, response)
        return response, self.state

    def is_memory_complete(self) -> bool:
        """Verify whether all required navigation slots are filled."""
        return all(self.slot_memory[k] is not None for k in ["sector", "warpFactor", "clearanceCode"])

    def _log_turn(self, inp: str, s_prev: str, s_next: str, out: str) -> None:
        self.history.append({
            "input": inp,
            "previous_state": s_prev,
            "next_state": s_next,
            "output": out,
            "slots": dict(self.slot_memory)
        })


class ShannonNoisyChannel:
    """
    Shannon Noisy Subspace Channel Model
    Bandwidth limit: Maximum 7 words per burst
    Injected noise tokens: {Banana, Labyrinth, Quantum, Midnight, Velocity, Green, Cosmological}
    """

    NOISE_VOCABULARY = [
        "Banana", "Labyrinth", "Quantum", "Midnight", "Velocity", "Green", "Cosmological"
    ]

    def __init__(self, max_words: int = 7, seed: Optional[int] = 42):
        self.max_words = max_words
        if seed is not None:
            random.seed(seed)

    def transmit(self, text: str) -> Dict[str, Any]:
        """
        Enforce max-word budget, inject plasma noise token, and compute Shannon entropy.
        """
        raw_tokens = text.strip().split()
        truncated = False
        if len(raw_tokens) > self.max_words:
            raw_tokens = raw_tokens[:self.max_words]
            truncated = True

        clean_text = " ".join(raw_tokens)
        corrupted_tokens = list(raw_tokens)
        injected = []

        if corrupted_tokens:
            idx = random.randint(0, len(corrupted_tokens) - 1)
            noise_word = random.choice(self.NOISE_VOCABULARY)
            corrupted_tokens[idx] = noise_word
            injected.append(noise_word)

        channel_output = " ".join(corrupted_tokens)
        entropy = self.compute_shannon_entropy(channel_output)

        return {
            "clean_input": text,
            "transmitted_clean": clean_text,
            "channel_output": channel_output,
            "word_count": len(corrupted_tokens),
            "truncated": truncated,
            "injected_noise": injected,
            "shannon_entropy_bits": entropy
        }

    @staticmethod
    def compute_shannon_entropy(text: str) -> float:
        """
        Compute Shannon Information Entropy H(X) = -sum p(x) * log2(p(x))
        across word tokens in bits/word.
        """
        tokens = [t.lower() for t in re.findall(r'\b\w+\b', text)]
        if not tokens:
            return 0.0
        n = len(tokens)
        counts: Dict[str, int] = {}
        for t in tokens:
            counts[t] = counts.get(t, 0) + 1
        
        entropy = 0.0
        for count in counts.values():
            p = count / n
            entropy -= p * math.log2(p)
        return round(entropy, 4)

    @staticmethod
    def compute_channel_capacity(bandwidth_hz: float, snr_linear: float) -> float:
        """
        Shannon-Hartley Theorem: C = W * log2(1 + S/N)
        """
        return round(bandwidth_hz * math.log2(1.0 + snr_linear), 4)


def demo_execution():
    """Demonstrate FST transitions and Noisy Channel encoding."""
    fst = FSTDialogueManager()
    channel = ShannonNoisyChannel(max_words=7, seed=77)

    print("=== SQUADRON WINOGRAD: FST INITIALIZATION ===")
    dialogue_steps = [
        "Hello AURA online",
        "Sirius binary waypoint",
        "Set warp factor 7",
        "Clearance authorization ALPHA-7",
        "Confirm navigation lock"
    ]

    for step in dialogue_steps:
        resp, state = fst.process_utterance(step)
        print(f"Cadet -> {step}")
        print(f"AURA  -> [{state}] {resp}")
        print(f"Slots -> {fst.slot_memory}\n")

    print("=== SQUADRON WINOGRAD: NOISY SUBSPACE TELEMETRY ===")
    msg = "Orbital entry vector locked into Sirius B telemetry"
    res = channel.transmit(msg)
    print(f"Original Input:    {res['clean_input']}")
    print(f"Clamped (7 words): {res['transmitted_clean']}")
    print(f"Channel Output:    {res['channel_output']}")
    print(f"Shannon Entropy:   {res['shannon_entropy_bits']} bits/word")


if __name__ == "__main__":
    demo_execution()
