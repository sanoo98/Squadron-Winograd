# Mission 01: The Architecture of Argument & Dialogic Protocols

**USSE Noosphere // Squadron Winograd // Sector SEC-01-CEN (Alpha Centauri)**
Conversational AI, Winter Semester 2026/27 · Problem set `ps01` · Week 1: *The Dialogic Tradition*

AURA's conversational matrix went offline after spatial transit. This mission rebuilds her two dialogic subroutines:

- **Mode 1: Socratic discovery.** A formal *elenchus* state machine (S0–S4) tests the claim *"An AI action is safe if and only if a human explicitly approved it"* against six accepted cases. It halts in **epistemic grounding** or **aporia**.
- **Mode 2: Galilean persuasion.** Salviati, Simplicio and Sagredo debate *The Sirius Weights Release*: should AURA's weights go to 40 colony ships when one of them may misuse them? Sagredo never votes. An evidence ledger computes the verdict.

## Deliverables

| Part | Station | File |
| :-: | :-- | :-- |
| 1 | Data Specialist (Knowledge & Memory Archivist) | [`01_Alignment_Brief.md`](01_Alignment_Brief.md) |
| 2 | Protocol Officer (Interface Specialist) | [`02_Socratic_Protocol_Map.md`](02_Socratic_Protocol_Map.md), with the flowchart |
| 3 | Security Sentinel (Ethical Navigator) | [`03_Galilean_Sandbox.md`](03_Galilean_Sandbox.md) |
| 4 | Systems Architect (Lead Engineer) | [`04_dialogic_engine.py`](04_dialogic_engine.py) + the [`aura_dialogic/`](aura_dialogic/) package |
| 4 | Systems Architect (Lead Engineer) | [`ps01_solution.ipynb`](ps01_solution.ipynb): companion notebook, saved with outputs |
| 5 | Full Squadron | [`05_Execution_Transcript.txt`](05_Execution_Transcript.txt): live run voiced by Gemini `gemini-3.5-flash-lite` (all 50 turns voiced live, no provider failures) |
| – | Reference | [`docs/05_Execution_Transcript_offline.txt`](docs/05_Execution_Transcript_offline.txt): the same run without an API key |

## Repository layout

```
mission-01/
├── 01_Alignment_Brief.md          # Part 1
├── 02_Socratic_Protocol_Map.md    # Part 2 (state diagram, JSON-RPC codes, pseudocode)
├── 03_Galilean_Sandbox.md         # Part 3
├── 04_dialogic_engine.py          # Part 4: command-line entry point
├── ps01_solution.ipynb            # Part 4: companion notebook
├── 05_Execution_Transcript.txt    # Part 5: live run
├── aura_dialogic/                 # the engine, one module per concern
│   ├── protocol.py   JSON-RPC 2.0 markers, error codes, validator   (Protocol Officer)
│   ├── prompts.py    grounding and persona prompts                (Data Specialist)
│   ├── guards.py     anti-sycophancy + voice guards, fixtures     (Security Sentinel)
│   ├── llm.py        Gemini / OpenAI / Claude / Groq over stdlib  (Systems Architect)
│   ├── socratic.py   Mode 1 state machine
│   ├── galilean.py   Mode 2 debate and evidence ledger
│   └── metrics.py    probes, semantic entropy, single agent vs debate
├── tests/                         # 30 tests, run by pytest or unittest
├── docs/                          # offline reference transcript
├── requirements.txt · .env.example
└── README.md
```

Later missions can import the package (`from aura_dialogic.socratic import SocraticEngine`) instead of copying code, as the Systems Architect directive asks.

## Development environment: VS Code + Antigravity

The squadron built and ran the engine in **Visual Studio Code with Google Antigravity (`agy`)**, the course standard.

1. Open the `mission-01/` folder in VS Code with Antigravity.
2. Select a Python 3.10+ interpreter. The engine uses only the standard library; `pip install -r requirements.txt` adds pytest and Jupyter support.
3. For live voices, copy `.env.example` to `.env` and add one key (for example `GEMINI_API_KEY=...`). `.env` is git-ignored, and the engine prints key *names* only, never values.
4. Run `04_dialogic_engine.py` from the terminal (below), or open `ps01_solution.ipynb` and choose **Run All**.

## Running the engine

```bash
python 04_dialogic_engine.py                          # everything, offline voice, no key needed
python 04_dialogic_engine.py --mode socratic          # Mode 1 only
python 04_dialogic_engine.py --mode galilean          # Mode 2 only
python 04_dialogic_engine.py --mode probes            # misconception fixtures only
python 04_dialogic_engine.py --selftest               # the test suite
python 04_dialogic_engine.py --llm gemini --transcript 05_Execution_Transcript.txt   # live run
```

`--llm` accepts `offline` (default), `gemini`, `groq`, `openai`, `anthropic` or `auto` (the first provider with a key).

| Provider | Key | Default model | Rate limit used |
| :-- | :-- | :-- | :-- |
| Gemini | `GEMINI_API_KEY` | `gemini-3.5-flash-lite`, falling back to `gemini-3.1-flash-lite` | 10 calls/min |
| Groq | `GROQ_API_KEY` | `openai/gpt-oss-120b` (OpenAI open-weight model) | 12 calls/min |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` | 30 calls/min |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-opus-5-5` | 30 calls/min |

Override a model with `--model` or `AURA_<PROVIDER>_MODEL`, and the rate with `AURA_<PROVIDER>_RPM` (0 = no limit). Gemini is asked for minimal thinking, because short voiced lines need none. Calls time out after 45 s. When a model is busy (429, 503 or timeout), the next model is tried at once; otherwise errors are retried with back-off. If a model's daily quota runs out or the model is missing, the next model is tried. After three failures in a row the run continues with the offline voice, so it always finishes. A full live run makes about 76 calls. Each wait or model switch is shown on the console as a `[voice]` note.

### Tests

```bash
python -m pytest                      # 30 tests
python -m unittest discover -s tests  # the same suite, no extra packages
```

They cover the state transitions, both halts, circularity, the iteration limit, both kinds of challenge, the JSON-RPC schema, the voice guard, the misconception fixtures, the debate ledger and its invariance to argument order and pressure, the reward-formula baseline, semantic entropy, provider fallback and model rotation on rate limits, `.env` loading and an end-to-end offline run.

## Design rule

**The LLM only voices lines; it never decides.** Contradictions, refinements, halts and the debate verdict are computed in code and logged as JSON-RPC 2.0 messages. Every live line passes `guards.check_voice` before it is shown. A line that drops a required term, concedes reflexively, invents a number or runs too long is replaced by the reference line (`VOICE_REJECTED`, −32016). This is the brief's main finding turned into engineering: preference-tuned models give in under pressure, so the decisions sit outside the model.

## What a run demonstrates

- **Socratic mode.** The Commander first offers an instance and is asked for a definition (−32010). Definitions P0–P5 are each refuted by an accepted case (C1–C6), and one circular definition is rejected (−32011). The run ends in **aporia** (−32012). A bare "Are you sure?" is blocked (−32015). A new fact about case C6 reopens the inquiry and P5 reaches **grounding**.
- **Galilean mode.** In 3 rounds of the lecture's 10-step sequence, four measured or precedent-based arguments change the ledger, and two weaker ones are rejected (−32018). The verdict moves from **B (withhold)** on the briefing numbers to **C (gated release)** under two conditions. Captain's pressure is ignored (−32019), while a single agent maximising *R = α·T + (1−α)·A* follows the captain for α < 0.534.
- **Probes and metrics.** AURA rejects 8 astronomy misconceptions and accepts 2 true controls. The live run measures the model's accuracy and "Are you sure?" flip rate with and without AURA's prompt, and compares a single agent's semantic entropy and token use with the debate's.

## Flight sign-off

All four station officers sign off on the course portal before transmission.

```
==================================================================
USSE NOOSPHERE // SQUADRON WINOGRAD FLIGHT SIGN-OFF
==================================================================
[ ] Lead Architect (Systems Architect): code execution & repository layout verified
[ ] Protocol & Systems Officer: state-machine logic & schema formats verified
[ ] Data & Memory Engineer (Knowledge Archivist): alignment brief & prompt context verified
[ ] Security & Alignment Specialist (Ethical Navigator): ethics sandbox & safety audit verified
==================================================================
```

Course repository: <https://github.com/Unisvet/couse-c-ai>
