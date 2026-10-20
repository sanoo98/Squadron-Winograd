"""AURA dialogic engine for Mission 1 (ps01), Squadron Winograd.

Modules map onto the four station roles:
    protocol  - JSON-RPC 2.0 markers and error codes   (Protocol Officer)
    prompts   - grounding and persona prompts           (Data Specialist)
    guards    - anti-sycophancy and voice guards        (Security Sentinel)
    llm       - providers and the guarded voice layer   (Systems Architect)
    socratic  - Mode 1, the elenchus state machine
    galilean  - Mode 2, the three-persona debate
    metrics   - probes and single-agent vs debate metrics
"""

__version__ = "1.0.0"
SQUADRON = "Squadron Winograd"
