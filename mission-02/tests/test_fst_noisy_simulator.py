"""
Unit Tests for Squadron Winograd Mission 02 Simulator
Station Officer: Muhammad Qasim Siddiqui (Systems Architect)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from importlib import import_module
sim = import_module("04_fst_noisy_simulator")
FSTDialogueManager = sim.FSTDialogueManager
ShannonNoisyChannel = sim.ShannonNoisyChannel


def test_fst_nominal_journey():
    """Verify nominal 5-state trajectory from INIT to TERMINAL."""
    fst = FSTDialogueManager()
    assert fst.state == FSTDialogueManager.STATE_INIT

    # 1. Wake
    resp, state = fst.process_utterance("Hello AURA online")
    assert state == FSTDialogueManager.STATE_GREETING

    # 2. Sector
    resp, state = fst.process_utterance("Plot trajectory to Sirius")
    assert state == FSTDialogueManager.STATE_COLLECT_SLOTS
    assert fst.slot_memory["sector"] is not None

    # 3. Velocity
    resp, state = fst.process_utterance("Engage Warp 8")
    assert state == FSTDialogueManager.STATE_COLLECT_SLOTS
    assert fst.slot_memory["warpFactor"] == "Warp 8"

    # 4. Clearance
    resp, state = fst.process_utterance("Authorization code ALPHA-7")
    assert state == FSTDialogueManager.STATE_CONFIRMATION
    assert fst.slot_memory["clearanceCode"] == "ALPHA-7"

    # 5. Confirmation
    resp, state = fst.process_utterance("Confirm trajectory engage")
    assert state == FSTDialogueManager.STATE_TERMINAL
    assert fst.is_memory_complete() is True


def test_fst_emergency_reset():
    """Verify emergency reset purges all slots and reverts state to INIT."""
    fst = FSTDialogueManager()
    fst.process_utterance("Hello AURA")
    fst.process_utterance("Sirius")
    assert fst.slot_memory["sector"] is not None

    resp, state = fst.process_utterance("Emergency reset system now")
    assert state == FSTDialogueManager.STATE_INIT
    assert fst.slot_memory["sector"] is None
    assert fst.slot_memory["warpFactor"] is None
    assert fst.slot_memory["clearanceCode"] is None


def test_fst_unrecognized_input_fallback():
    """Verify unexpected user syntax transitions into FALLBACK."""
    fst = FSTDialogueManager()
    resp, state = fst.process_utterance("Sing me a pirate song")
    assert state == FSTDialogueManager.STATE_FALLBACK
    assert fst.fallback_count == 1


def test_noisy_channel_budget_clamp():
    """Verify messages longer than 7 words are strictly clamped."""
    channel = ShannonNoisyChannel(max_words=7, seed=42)
    long_msg = "AURA telemetry stream approaching Sirius B white dwarf high radiation zone"
    res = channel.transmit(long_msg)
    assert res["word_count"] <= 7
    assert res["truncated"] is True


def test_noisy_channel_noise_vocabulary():
    """Verify channel output contains a word from the Sirius noise vocabulary."""
    channel = ShannonNoisyChannel(max_words=7, seed=101)
    res = channel.transmit("AURA report telemetry status")
    tokens = res["channel_output"].split()
    matched = [w for w in tokens if w in ShannonNoisyChannel.NOISE_VOCABULARY]
    assert len(matched) >= 1


def test_shannon_entropy_calculation():
    """Verify entropy calculations for uniform and identical distributions."""
    # Identical tokens -> 0 bits
    zero_ent = ShannonNoisyChannel.compute_shannon_entropy("quantum quantum quantum")
    assert zero_ent == 0.0

    # 4 distinct tokens -> 2.0 bits
    four_ent = ShannonNoisyChannel.compute_shannon_entropy("banana labyrinth quantum midnight")
    assert four_ent == 2.0


def test_shannon_hartley_capacity():
    """Verify channel capacity formula: C = W * log2(1 + S/N)."""
    cap = ShannonNoisyChannel.compute_channel_capacity(1000.0, 7.0)
    assert cap == 3000.0
