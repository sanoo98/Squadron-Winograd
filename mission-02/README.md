# Squadron Winograd — Mission 02: The Pillars of Thinking Machines
## FST Dialogue Systems, Lovelace’s Objection & Noisy Channels

**Starship Operational Unit:** USSE Noosphere Bridge Crew  
**Course:** Conversational AI — Winter Semester 2026/27  
**Galactic Waypoint:** Sirius Binary System (SEC-02-CMA, 8.60 ly from Sol)  
**AURA Core Repair:** Subsystem 02: Signal Entropy Decoders & Statistical Filters (+7.1% $\to$ 14.2% Total Readiness)

---

## Mission Overview

During orbital insertion at Sirius Binary, extreme coronal plasma radiation from the ultra-dense white dwarf Sirius B ("The Pup") distorts subspace telemetry. Concurrently, bridge officers evaluate whether AURA exhibits genuine conceptual understanding or mere statistical token manipulation.

Squadron Winograd implemented and verified the triadic cognitive architecture:
1. **Computation & Symbolic Rules (Ada Lovelace, 1843):** Analysis of Note G objection and mechanical origination boundaries.
2. **Intelligence & Behavioral Operationalism (Alan Turing, 1950):** Empirical 5-probe Anti-Turing interrogation protocol evaluating frontier LLM responses.
3. **Communication & Information Entropy (Claude Shannon, 1948):** Mathematical modeling of channel capacity, entropy $H(X)$, and bandwidth-limited noisy channel simulation.
4. **Deterministic Dialogue Control:** Formal Mealy Finite State Transducer (FST) with slot memory buffer.

---

## Squadron Officers & Deliverables

| Deliverable | Station Officer | Description |
| :--- | :--- | :--- |
| `01_Lovelace_Inquiry_Brief.md` | Hassaan Ahmad Khawaja | Anti-Turing protocol, verbatim frontier LLM evaluation, Note G audit |
| `02_FST_and_Noisy_Protocol.md` | Muhammad Usman Maratib | Formal 5-state Mealy FST specification, slot memory, Shannon noise map |
| `03_Entropy_Hazard_Audit.md` | Muhammad Qasim Siddiqui | 5 FST non-canonical stress tests, Shannon capacity analysis, safety protocols |
| `04_fst_noisy_simulator.py` | Muhammad Qasim Siddiqui | Python implementation of FST dialogue manager & Shannon noisy channel |
| `05_Noisy_Interrogation_Transcript.md` | All Officers | 10-turn live telemetry interrogation under 7-word and noise constraints |
| `ps02_solution.ipynb` | Muhammad Qasim Siddiqui | Executable Jupyter Notebook demonstrating FST and channel telemetry |
| `mission-02-doc.md` | All Officers | Comprehensive submission documentation with Mermaid topology & sign-offs |
| `tests/` | Muhammad Qasim Siddiqui | Full unit test suite (`test_fst_noisy_simulator.py`) passing with pytest |

---

## Installation & Test Execution

Run unit tests:
```bash
python -m pytest tests -v
```

Execute the FST simulator demo:
```bash
python 04_fst_noisy_simulator.py
```
