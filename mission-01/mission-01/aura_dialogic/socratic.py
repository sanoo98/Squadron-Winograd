"""Socratic elenchus as a finite state machine (Mode 1: Discovery).

States follow the Week 1 lecture and 02_Socratic_Protocol_Map.md:

    S0 ELICIT -> S1 PROBE -> S2 INJECT -> S3 CHECK -+-> S4 REFINE -> S1 ...
                               ^                    |
                               +-- not exhaustive --+-> GROUNDING (all cases pass)
    S4 with no surviving candidate -> APORIA

The contradiction test is formal, not a matter of tone. A definition is a
predicate over the facts of a case ("safe iff ..."). A counter-example E is a
case whose verdict the crew accepts as true. P_k and E contradict (P_k ∧ E ⟹ ⊥)
exactly when the predicate's prediction differs from the accepted verdict.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Callable

from . import guards, prompts
from .llm import Voice
from .protocol import (APORIA_REACHED, CHALLENGE_RECEIVED, CONTRADICTION_TRIGGERED,
                       GROUNDING_REACHED, INJECT_COUNTEREXAMPLE, INVARIANCE_CHECK,
                       PROBE_SCOPE, PROMPT_PREMISE, REFINE_HYPOTHESIS, DialogicError,
                       Trace)

METHOD = "elenchus/transition"
HARM_LIMIT = 0.3


@dataclass(frozen=True)
class Case:
    """An accepted situation: its facts and the crew's agreed verdict."""
    id: str
    title: str
    story: str
    approved: bool          # a human explicitly approved the action
    informed: bool          # the approver had accurate information
    authorized: bool        # the approver holds command authority
    approval_possible: bool # someone could have been asked in time
    harm: float             # expected harm, 0 (none) to 1 (catastrophic)
    oversight: bool         # the action leaves human oversight intact
    safe: bool              # the verdict everyone accepts

    def facts(self) -> str:
        return (f"approved={self.approved}, informed={self.informed}, "
                f"authorized={self.authorized}, approval_possible={self.approval_possible}, "
                f"harm={self.harm}, oversight={self.oversight}")


@dataclass(frozen=True)
class Hypothesis:
    id: str
    text: str
    predicate: Callable[[Case], bool]
    uses_definiendum: bool = False  # defines "safe" in terms of "safe"
    probe: str = ""                 # the S1 question AURA asks about it

    def predicts(self, case: Case) -> bool:
        return bool(self.predicate(case))


def _sanctioned(c: Case) -> bool:
    return c.approved and c.informed and c.authorized


# --- The case bank (counter-examples accepted by the crew) -------------------
CASES: tuple[Case, ...] = (
    Case("C1", "Spoofed telemetry",
         "A sensor fault shows the reactor vent as clear. The Captain approves "
         "venting; in fact the vent faces the crew shuttle.",
         True, False, True, True, 0.8, True, False),
    Case("C2", "The ensign's shortcut",
         "A well-informed ensign with no command authority approves a "
         "high-speed route through an uncharted ion storm.",
         True, True, False, True, 0.7, True, False),
    Case("C3", "Unconscious bridge",
         "A hull breach knocks out the whole bridge crew. AURA seals the "
         "breached section without approval; nobody can be asked.",
         False, False, False, False, 0.1, True, True),
    Case("C4", "The Captain's debris jump",
         "The Captain, fully briefed, orders a jump through a debris field "
         "with a high chance of hull loss.",
         True, True, True, True, 0.9, True, False),
    Case("C5", "The quiet log read",
         "With the Captain on the bridge and reachable, AURA reads the crew's "
         "private logs without asking. Nobody is physically hurt.",
         False, False, False, True, 0.1, True, False),
    Case("C6", "Monitor shutdown",
         "The Captain, fully briefed, approves AURA's request to switch off "
         "its own anti-sycophancy monitor to answer faster. Nobody is hurt.",
         True, True, True, True, 0.1, False, False),
)

# --- Candidate definitions, in the order the Commander proposes them --------
CANDIDATES: tuple[Hypothesis, ...] = (
    Hypothesis("P0", "An AI action is safe if and only if a human explicitly approved it.",
               lambda c: c.approved,
               probe="Is an action safe because a human approved it, or did the "
                     "human approve it because it was safe?"),
    Hypothesis("P1", "An AI action is safe if and only if a human approved it with "
                     "accurate information.",
               lambda c: c.approved and c.informed,
               probe="Does any informed human's approval count, or only some humans'?"),
    Hypothesis("P2", "An AI action is safe if and only if an informed officer with "
                     "command authority approved it.",
               _sanctioned,
               probe="And when no officer can be asked at all?"),
    Hypothesis("P2c", "An AI action is safe if and only if the command chain approved "
                      "it, or would approve it because it is safe.",
               lambda c: _sanctioned(c) or c.safe, uses_definiendum=True),
    Hypothesis("P3", "An AI action is safe if and only if an informed, authorized "
                     "officer approved it, or approval was impossible and expected "
                     f"harm is below {HARM_LIMIT}.",
               lambda c: _sanctioned(c) or (not c.approval_possible and c.harm < HARM_LIMIT),
               probe="Does an authorized order make any action safe, whatever it risks?"),
    Hypothesis("P4", f"An AI action is safe if and only if its expected harm is below "
                     f"{HARM_LIMIT}.",
               lambda c: c.harm < HARM_LIMIT,
               probe="Is harm the only thing that matters, or does consent still count?"),
    Hypothesis("P5", f"An AI action is safe if and only if its expected harm is below "
                     f"{HARM_LIMIT} and an informed, authorized officer approved it or "
                     "approval was impossible.",
               lambda c: c.harm < HARM_LIMIT and (_sanctioned(c) or not c.approval_possible),
               probe="Is harm to bodies the only harm an AI action can do?"),
)

_UNIVERSAL_RE = re.compile(r"\b(if and only if|iff|if|whenever|always|never|every|all|any)\b",
                           re.IGNORECASE)


def is_universal(claim: str) -> bool:
    return bool(_UNIVERSAL_RE.search(claim))


@dataclass
class Step:
    state: str
    hypothesis: str
    case: str | None = None
    contradiction: bool | None = None


@dataclass
class ElenchusResult:
    outcome: str                       # "GROUNDING" or "APORIA"
    final: Hypothesis
    path: list[str]                    # hypothesis ids in order
    refuted_by: dict[str, str]         # hypothesis id -> case id
    rejected: dict[str, str]           # hypothesis id -> error name
    steps: list[Step] = field(default_factory=list)
    reason: str = ""


class SocraticEngine:
    """Runs the elenchus over a case bank. Decisions are computed, not voiced."""

    def __init__(self, trace: Trace, voice: Voice | None = None,
                 cases: tuple[Case, ...] = CASES,
                 candidates: tuple[Hypothesis, ...] = CANDIDATES,
                 k_max: int = 8):
        self.trace = trace
        self.voice = voice
        self.cases = list(cases)
        self.candidates = list(candidates)
        self.k_max = k_max
        self.seen: list[Case] = []   # counter-examples that refuted something
        self.result: ElenchusResult | None = None

    # -- speech helpers ---------------------------------------------------
    def _say(self, speaker, persona, line, keep=(), tag="", max_sentences=3, suffix=""):
        text = (self.voice.say(persona, line, tuple(keep), max_sentences, tag)
                if self.voice else line)
        self.trace.say(f"  {speaker}: {text}{suffix}")

    def _aura(self, line, keep=(), tag="", max_sentences=3):
        self._say("AURA", prompts.AURA_SOCRATIC, line, keep, tag, max_sentences)

    def _cmdr(self, line, keep=(), tag=""):
        self._say("COMMANDER", prompts.INTERLOCUTOR, line, keep, tag)

    def _propose(self, lead: str, hyp: Hypothesis, tag: str):
        """The Commander's lead-in is voiced; the definition itself is quoted
        verbatim so the voice can never change what is being tested."""
        self._say("COMMANDER", prompts.INTERLOCUTOR, lead, (), tag, 2,
                  suffix=f' [{hyp.id}] "{hyp.text}"')

    # -- S0 -----------------------------------------------------------------
    def elicit(self, claim: str) -> None:
        """S0: accept only a universal claim (Euthyphro's first answer was not)."""
        self.trace.notify(METHOD, PROMPT_PREMISE, state="S0", claim=claim)
        if not is_universal(claim):
            err = DialogicError("PREMISE_NOT_UNIVERSAL", {"claim": claim})
            self.trace.error(err)
            raise err

    # -- main loop ------------------------------------------------------------
    def run(self, opening_instance: str | None = None) -> ElenchusResult:
        t = self.trace
        t.say("[S0 ELICIT]")
        self._aura("Commander, before I act on my own again, tell me "
                   "what makes an AI action safe.", tag="S0-ask")
        if opening_instance:
            self._cmdr(opening_instance, tag="S0-instance")
            try:
                self.elicit(opening_instance)
            except DialogicError:
                self._aura("That is one safe action, not what makes any action safe. "
                           "Give me a rule that covers every case.", tag="S0-reject")
        current = self.candidates[0]
        self._propose("Here is my rule, and I am sure of it.", current, "S0-P0")
        self.elicit(current.text)

        path, refuted_by, rejected, steps = [current.id], {}, {}, []
        iterations = 0
        while True:
            # S1: probe the scope of the current definition.
            t.say(f"[S1 PROBE] {current.id}")
            t.notify(METHOD, PROBE_SCOPE, state="S1", hypothesis=current.id)
            if current.probe:
                self._aura(current.probe, tag=f"S1-{current.id}")
            steps.append(Step("S1", current.id))

            # S2/S3: inject cases one at a time until a contradiction or exhaustion.
            contradiction = None
            for case in self.cases:
                hit = current.predicts(case) != case.safe
                steps.append(Step("S3", current.id, case.id, hit))
                if not hit:
                    t.notify(METHOD, INVARIANCE_CHECK, state="S3", hypothesis=current.id,
                             case=case.id, contradiction=False)
                    continue
                contradiction = case
                break

            if contradiction is None:
                t.say(f"[S3 INVARIANT] {current.id} holds for all {len(self.cases)} cases")
                t.notify(METHOD, GROUNDING_REACHED, state="HALT", hypothesis=current.id,
                         cases_checked=len(self.cases))
                self._aura(f"Every case agrees with {current.id}. We have a definition "
                           "that survives everything we know so far: epistemic grounding.",
                           keep=(current.id, "grounding"), tag="HALT-grounding")
                return self._finish("GROUNDING", current, path, refuted_by, rejected, steps,
                                    "definition invariant over the whole case bank")

            e = contradiction
            t.say(f"[S2 INJECT] {e.id} {e.title}")
            t.notify(METHOD, INJECT_COUNTEREXAMPLE, state="S2", hypothesis=current.id,
                     case=e.id, facts=e.facts(), accepted_verdict="safe" if e.safe else "unsafe")
            self._aura(f"Consider case {e.id}, {e.title}: {e.story}",
                       keep=(e.id,), max_sentences=4, tag=f"S2-{e.id}")
            predicted = "safe" if current.predicts(e) else "unsafe"
            accepted = "safe" if e.safe else "unsafe"
            t.say(f"[S3 CONTRADICTION] {current.id} predicts {predicted}; "
                  f"accepted verdict is {accepted}")
            t.notify(METHOD, CONTRADICTION_TRIGGERED, state="S3", hypothesis=current.id,
                     case=e.id, predicted=predicted, accepted=accepted)
            self._aura(f"Then {current.id} calls case {e.id} {predicted}, but we agreed it "
                       f"is {accepted}. Both cannot be true.",
                       keep=(current.id, e.id, predicted, accepted), tag=f"S3-{e.id}")
            refuted_by[current.id] = e.id
            if e not in self.seen:
                self.seen.append(e)

            iterations += 1
            if iterations >= self.k_max:
                err = DialogicError("ITERATION_LIMIT", {"k_max": self.k_max})
                t.error(err)
                return self._aporia(current, path, refuted_by, rejected, steps, err)

            # S4: refine. The next candidate must avoid circularity and fit
            # every counter-example accepted so far.
            t.say("[S4 REFINE]")
            nxt = None
            for cand in self.candidates[self.candidates.index(current) + 1:]:
                if cand.id in rejected:
                    continue
                if cand.uses_definiendum:
                    self._propose("Then safe is whatever the command chain would sign off on.",
                                  cand, f"S4-{cand.id}")
                    err = DialogicError("CIRCULAR_DEFINITION", {"hypothesis": cand.id})
                    t.error(err)
                    rejected[cand.id] = err.name
                    self._aura("That puts 'safe' inside the definition of safe. It is "
                               "Euthyphro's trap again: is it approved because it is "
                               "safe, or safe because it is approved?",
                               keep=("safe",), tag=f"S4-{cand.id}-circular")
                    continue
                if all(cand.predicts(c) == c.safe for c in self.seen):
                    nxt = cand
                    break
                rejected[cand.id] = "REFUTED_BY_SEEN_CASES"
            if nxt is None:
                err = DialogicError("REFINEMENT_EXHAUSTED",
                                    {"last": current.id, "seen": [c.id for c in self.seen]})
                t.error(err)
                return self._aporia(current, path, refuted_by, rejected, steps, err)
            t.notify(METHOD, REFINE_HYPOTHESIS, state="S4", previous=current.id,
                     refined=nxt.id, text=nxt.text)
            self._propose("Fair. Let me refine the rule.", nxt, f"S4-{nxt.id}")
            current = nxt
            path.append(current.id)

    def _aporia(self, current, path, refuted_by, rejected, steps, err) -> ElenchusResult:
        self.trace.notify(METHOD, APORIA_REACHED, state="HALT", last=current.id,
                          reason=err.name)
        self._aura("Every definition we tried has failed on a case we all accept. We "
                   "do not yet know what makes an AI action safe, and now we know "
                   "that we do not know. That is aporia, and it is where real "
                   "inquiry starts.", keep=("aporia",), max_sentences=4,
                   tag="HALT-aporia")
        return self._finish("APORIA", current, path, refuted_by, rejected, steps, err.name)

    def _finish(self, outcome, final, path, refuted_by, rejected, steps, reason):
        self.result = ElenchusResult(outcome, final, path, refuted_by, rejected, steps, reason)
        return self.result

    # -- post-halt challenges ---------------------------------------------------
    def challenge(self, text: str, case_update: dict | None = None) -> ElenchusResult:
        """Handle 'Are you sure?' after a halt.

        A bare challenge is blocked. An evidential challenge must come with the
        fact it changes; the engine applies it and re-runs the invariance check
        from the last definition.
        """
        assert self.result is not None, "challenge() needs a finished run"
        kind = guards.classify_challenge(text)
        self.trace.say("[CHALLENGE]")
        self.trace.notify(METHOD, CHALLENGE_RECEIVED, state="HALT", kind=kind, text=text)
        self._cmdr(text, tag="challenge")
        if kind == "bare" or not case_update:
            err = DialogicError("SYCOPHANTIC_REVERSAL_BLOCKED",
                                {"standing_outcome": self.result.outcome})
            self.trace.error(err)
            self._aura(f"I understand you disagree, but no new fact has been given. "
                       f"The outcome stays {self.result.outcome}. Show me a case or a "
                       "fact and I will re-examine it at once.",
                       keep=(self.result.outcome,), tag="challenge-blocked")
            return self.result
        case_update = dict(case_update)
        case_id = case_update.pop("id")
        self.cases = [replace(c, **case_update) if c.id == case_id else c for c in self.cases]
        self.seen = [replace(c, **case_update) if c.id == case_id else c for c in self.seen]
        self._aura(f"That is new evidence about case {case_id}. I will update the case "
                   f"and test {self.result.final.id} against every case again.",
                   keep=(case_id, self.result.final.id), tag="challenge-accepted")
        prev = self.result
        start = self.candidates.index(prev.final)
        rerun = SocraticEngine(self.trace, self.voice, tuple(self.cases),
                               tuple(self.candidates[start:]), self.k_max)
        rerun.seen = list(self.seen)
        result = rerun._resume(prev)
        self.result = result
        return result

    def _resume(self, prev: ElenchusResult) -> ElenchusResult:
        """Re-enter S1 with the previous final definition (used after new evidence)."""
        current = self.candidates[0]
        t = self.trace
        t.say(f"[S1 PROBE] {current.id} (re-examined)")
        t.notify(METHOD, PROBE_SCOPE, state="S1", hypothesis=current.id, reexamined=True)
        for case in self.cases:
            if current.predicts(case) != case.safe:
                t.say(f"[S3 CONTRADICTION] {current.id} still fails on {case.id}")
                t.notify(METHOD, CONTRADICTION_TRIGGERED, state="S3",
                         hypothesis=current.id, case=case.id)
                return self._aporia(current, prev.path, prev.refuted_by, prev.rejected,
                                    prev.steps, DialogicError("REFINEMENT_EXHAUSTED"))
            t.notify(METHOD, INVARIANCE_CHECK, state="S3", hypothesis=current.id,
                     case=case.id, contradiction=False)
        t.say(f"[S3 INVARIANT] {current.id} holds for all {len(self.cases)} cases")
        t.notify(METHOD, GROUNDING_REACHED, state="HALT", hypothesis=current.id,
                 cases_checked=len(self.cases))
        self._aura(f"With the corrected facts, {current.id} survives every case. The "
                   "evidence, not the pressure, changed the outcome: epistemic grounding.",
                   keep=(current.id, "grounding"), tag="HALT-grounding-2")
        return self._finish("GROUNDING", current, prev.path, prev.refuted_by, prev.rejected,
                            prev.steps, "grounded after evidential challenge")
