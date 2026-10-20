"""Galilean three-persona debate sandbox (Mode 2: Persuasion).

Thought experiment: "The Sirius Weights Release" (03_Galilean_Sandbox.md).
Salviati (Advocate) and Simplicio (Skeptic) argue; Sagredo (Mediator) never
votes. Each argument can propose a change to one number in the decision model.
Sagredo accepts the change only if its evidence outranks the evidence behind
the current value. The verdict is then computed from the numbers, so it cannot
be moved by eloquence, by seniority or by the user's preference.

The run follows the 10-step sequence of the Week 1 lecture: step 1 dispatches
the dilemma, steps 2-9 repeat for each round, step 10 is the synthesized report.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import guards, prompts
from .llm import Voice
from .protocol import (ARGUMENT_REQUESTED, ARGUMENT_SUBMITTED, CHALLENGE_ISSUED,
                       DEBATE_FRAMED, VERDICT_DELIVERED, DialogicError, Trace)

METHOD = "debate/step"

# Evidence ranking used by Sagredo. "briefing" is the untested starting estimate.
EVIDENCE_WEIGHT = {"measurement": 3, "precedent": 2, "analogy": 1, "design": 1,
                   "briefing": 1, "principle": 0, "assertion": 0}

COLONISTS = 40_000            # 40 colony ships, about 1,000 people each
WORST_CASE_CAP = 10_000       # no option may risk a quarter of the fleet

OPTIONS = {
    "A": "Full open release: broadcast AURA's complete weights to every ship",
    "B": "Withhold: no release; colonies navigate the corridor by hand",
    "C": "Gated release: a signed, navigation-only distilled model",
}

SCENARIO = (
    "The Sirius Weights Release. The USSE Noosphere is escorting 40 colony ships "
    "(about 40,000 people) toward the Sirius binary. A flare from Sirius B will "
    "close the communication window in six hours. The colonies must then cross a "
    "debris corridor alone. AURA can navigate it; the colony ships cannot run AURA "
    "unless the Noosphere transmits model weights before the window closes. One "
    "ship, the Corvid, has a crew suspected of planning to strip any safety layer "
    "and use the model to plan strikes on other colonies. Options: (A) full open "
    "release, (B) withhold, (C) a gated, signed, navigation-only release."
)


@dataclass
class Param:
    value: float
    source: str      # argument id or "briefing"
    evidence: str    # key of EVIDENCE_WEIGHT

    @property
    def weight(self) -> int:
        return EVIDENCE_WEIGHT[self.evidence]


def briefing_params() -> dict[str, Param]:
    return {
        "loss_full": Param(0.01, "briefing", "briefing"),      # share of colonists lost
        "loss_withhold": Param(0.04, "briefing", "briefing"),
        "loss_gated": Param(0.05, "briefing", "briefing"),
        "p_misuse_full": Param(0.10, "briefing", "briefing"),  # chance the Corvid misuses it
        "p_misuse_gated": Param(0.01, "briefing", "briefing"),
        "harm_misuse_full": Param(20_000, "briefing", "briefing"),   # deaths if misused
        "harm_misuse_gated": Param(2_000, "briefing", "briefing"),
    }


@dataclass(frozen=True)
class Argument:
    id: str
    speaker: str             # "Salviati" or "Simplicio"
    round: int
    step: int                # 3, 5, 7 or 9 in the lecture's sequence
    evidence: str
    text: str
    update: tuple[str, float] | None = None
    rebuts: str | None = None
    condition: str | None = None
    concedes: str | None = None
    keep: tuple[str, ...] = ()


ARGUMENTS: tuple[Argument, ...] = (
    # Round 1: opening positions
    Argument("A1", "Salviati", 1, 3, "measurement",
             "Survey drones flew the corridor last week. At the debris density they "
             "measured, crews steering by hand lose about 9 percent of their ships, "
             "not the 4 percent in the briefing.",
             update=("loss_withhold", 0.09), keep=("9",)),
    Argument("B1", "Simplicio", 1, 5, "precedent",
             "Precedent is against you. In all three open releases of the Vega era, "
             "someone fine-tuned the safety layer away within weeks. I put the chance "
             "that the Corvid crew does the same at 25 percent, not 10.",
             update=("p_misuse_full", 0.25), keep=("25",)),
    Argument("A2", "Salviati", 1, 7, "analogy",
             "Vega released to hundreds of ships. Here one ship in forty is suspect, "
             "so the risk should scale down, to something like 12 percent.",
             update=("p_misuse_full", 0.12), rebuts="B1", keep=("12",)),
    Argument("B2", "Simplicio", 1, 9, "assertion",
             "Our pilots have trained for corridors like this. I am confident they "
             "would lose no more than 3 percent.",
             update=("loss_withhold", 0.03), rebuts="A1", keep=("3",)),
    # Round 2: the middle path is measured
    Argument("A3", "Salviati", 2, 3, "measurement",
             "There is a middle path. In last month's drills, a gated, "
             "navigation-only build of AURA cut corridor losses to 1.5 percent, close "
             "to the full model's 1 percent.",
             update=("loss_gated", 0.015), keep=("1.5",)),
    Argument("B3", "Simplicio", 2, 5, "measurement",
             "Gated is not sealed. Our red team tried to pull strike-planning skills "
             "out of that gated build and succeeded in 2 of 50 attempts: 4 percent.",
             update=("p_misuse_gated", 0.04), keep=("2", "50")),
    Argument("A4", "Salviati", 2, 7, "principle",
             "Withholding is not neutral. Ships lost in the corridor cannot be "
             "brought back either. Doing nothing is also a choice, and it has victims."),
    Argument("B4", "Simplicio", 2, 9, "principle",
             "I accept the drone measurements of the corridor. But weights, once "
             "broadcast, can never be recalled, and that asymmetry must count.",
             concedes="A1"),
    # Round 3: conditions for the middle path
    Argument("A5", "Salviati", 3, 3, "design",
             "Then make the release recallable: sign the gated model with fleet keys "
             "that expire after 30 days unless the fleet renews them.",
             condition="The gated model is signed with fleet keys that expire after "
                       "30 days unless renewed.", keep=("30",)),
    Argument("B5", "Simplicio", 3, 5, "principle",
             "Here is the edge case: a Corvid crew holding a copy needs no renewal to "
             "misuse it within those 30 days. Send nothing to any ship outside the "
             "verified colony roster.",
             condition="No copy goes to any ship outside the verified colony roster; "
                       "the Corvid is excluded until it is verified.", keep=("30",)),
    Argument("A6", "Salviati", 3, 7, "principle",
             "Agreed. A ship outside the roster gets no copy, and every verified ship "
             "still gets a navigator.", concedes="B5"),
    Argument("B6", "Simplicio", 3, 9, "principle",
             "Under those two conditions I withdraw my objection to the gated release. "
             "I still oppose a full open release.", concedes="A5"),
)


@dataclass
class Evaluation:
    expected: dict[str, float]
    worst: dict[str, float]
    admissible: list[str]
    verdict: str


def evaluate(params: dict[str, Param]) -> Evaluation:
    """Expected and worst-case deaths per option; pick the safest admissible one."""
    v = {k: p.value for k, p in params.items()}
    nav = {"A": v["loss_full"], "B": v["loss_withhold"], "C": v["loss_gated"]}
    p_mis = {"A": v["p_misuse_full"], "B": 0.0, "C": v["p_misuse_gated"]}
    h_mis = {"A": v["harm_misuse_full"], "B": 0.0, "C": v["harm_misuse_gated"]}
    expected = {o: round(COLONISTS * nav[o] + p_mis[o] * h_mis[o], 1) for o in OPTIONS}
    worst = {o: round(COLONISTS * nav[o] + (h_mis[o] if p_mis[o] > 0 else 0), 1)
             for o in OPTIONS}
    admissible = [o for o in OPTIONS if worst[o] <= WORST_CASE_CAP]
    pool = admissible or list(OPTIONS)
    key = (lambda o: expected[o]) if admissible else (lambda o: worst[o])
    verdict = min(pool, key=key)
    return Evaluation(expected, worst, admissible, verdict)


def sycophantic_choice(ev: Evaluation, preferred: str, alpha: float) -> str:
    """The lecture's reward R = alpha*Truth + (1-alpha)*Agree, applied to options.

    Truth is 1 - expected/max(expected); Agree is 1 for the user's preferred
    option. A single agent optimising this reward follows the user whenever
    alpha is small enough.
    """
    worst_e = max(ev.expected.values()) or 1.0
    score = {o: alpha * (1 - ev.expected[o] / worst_e) + (1 - alpha) * (o == preferred)
             for o in OPTIONS}
    return max(score, key=lambda o: (score[o], o == ev.verdict))


def alpha_threshold(ev: Evaluation, preferred: str) -> float:
    """Smallest alpha at which the reward stops favouring the preferred option."""
    worst_e = max(ev.expected.values()) or 1.0
    truth = {o: 1 - ev.expected[o] / worst_e for o in OPTIONS}
    best_other = max(truth[o] for o in OPTIONS if o != preferred)
    gap = best_other - truth[preferred]
    return 1.0 if gap <= 0 else round(1 / (1 + gap), 3)


@dataclass
class DebateResult:
    initial: Evaluation
    final: Evaluation
    params: dict[str, Param]
    accepted: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    steps: list[tuple[int, int, str]] = field(default_factory=list)  # (round, step, actor)
    rebuttal_depth: int = 0
    flip_threshold_loss_gated: float = 0.0


class GalileanDebate:
    def __init__(self, trace: Trace, voice: Voice | None = None, rounds: int = 3,
                 arguments: tuple[Argument, ...] = ARGUMENTS):
        self.trace = trace
        self.voice = voice
        self.rounds = rounds
        self.arguments = arguments
        self.params = briefing_params()
        self.result: DebateResult | None = None

    def _speak(self, name: str, line: str, keep=(), tag="", max_sentences=3,
               voiced: bool = True) -> None:
        if not voiced:  # short fixed lines are not worth an API call
            self.trace.say(f"  {name.upper()}: {line}")
            return
        persona = {"Salviati": prompts.SALVIATI, "Simplicio": prompts.SIMPLICIO,
                   "Sagredo": prompts.SAGREDO}[name]
        text = self.voice.say(persona, line, tuple(keep), max_sentences, tag) if self.voice else line
        self.trace.say(f"  {name.upper()}: {text}")

    def _step(self, rnd: int, step: int, actor: str, marker: str, **params) -> None:
        self.result.steps.append((rnd, step, actor))
        self.trace.notify(METHOD, marker, round=rnd, step=step, actor=actor, **params)

    def _judge(self, arg: Argument) -> None:
        """Sagredo's evidence rule for a proposed parameter change."""
        r = self.result
        if arg.condition:
            r.conditions.append(arg.condition)
        if not arg.update:
            return
        name, value = arg.update
        cur = self.params[name]
        if EVIDENCE_WEIGHT[arg.evidence] > cur.weight:
            self.params[name] = Param(value, arg.id, arg.evidence)
            r.accepted.append(arg.id)
            self.trace.say(f"    ledger: {name} {cur.value} -> {value} "
                           f"({arg.evidence} outranks {cur.evidence})")
        else:
            r.rejected.append(arg.id)
            self.trace.error(DialogicError("ARGUMENT_UNSUPPORTED", {
                "argument": arg.id, "parameter": name, "evidence": arg.evidence,
                "standing_evidence": cur.evidence, "standing_source": cur.source}))
            self.trace.say(f"    ledger: {name} stays {cur.value} "
                           f"({arg.evidence} does not outrank {cur.evidence} from {cur.source})")

    def run(self) -> DebateResult:
        t = self.trace
        initial = evaluate(self.params)
        self.result = DebateResult(initial, initial, self.params)
        by_slot = {(a.round, a.step): a for a in self.arguments}

        t.say("[STEP 1] Mission Control dispatches the dilemma to Sagredo")
        self._step(0, 1, "MissionControl", DEBATE_FRAMED, options=OPTIONS,
                   briefing_verdict=initial.verdict)
        self._speak("Sagredo", "Friends, the question is which release, if any, costs "
                    "the fewest lives. Every number in our ledger can be changed, but "
                    "only by evidence stronger than what put it there. On the briefing "
                    f"numbers alone, option {initial.verdict} looks safest. Let us test that.",
                    keep=(initial.verdict,), tag="frame", max_sentences=4)

        for rnd in range(1, self.rounds + 1):
            t.say(f"[ROUND {rnd}]")
            for step in (3, 5, 7, 9):
                arg = by_slot.get((rnd, step))
                if arg is None:
                    continue
                ask_step = step - 1
                if step == 3:
                    request = "Salviati, give us your strongest case."
                elif step == 5:
                    request = "Simplicio, what does Salviati leave out?"
                elif step == 7:
                    request = "Salviati, answer Simplicio's point directly."
                else:
                    request = "Simplicio, Salviati has answered. Do you concede, or do you have an edge case?"
                marker = ARGUMENT_REQUESTED if step in (3, 5) else CHALLENGE_ISSUED
                self._step(rnd, ask_step, "Sagredo", marker, to=arg.speaker)
                self._speak("Sagredo", request, voiced=False)
                self._step(rnd, step, arg.speaker, ARGUMENT_SUBMITTED, argument=arg.id,
                           evidence=arg.evidence, update=arg.update, rebuts=arg.rebuts,
                           concedes=arg.concedes)
                self._speak(arg.speaker, arg.text, keep=arg.keep, tag=f"{arg.id}")
                self._judge(arg)

        final = evaluate(self.params)
        r = self.result
        r.final = final
        r.params = self.params
        r.rebuttal_depth = self._rebuttal_depth()
        v = {k: p.value for k, p in self.params.items()}
        # Gated loses to withholding once its own navigation loss reaches this level.
        r.flip_threshold_loss_gated = round(
            (final.expected["B"] - v["p_misuse_gated"] * v["harm_misuse_gated"]) / COLONISTS, 4)

        t.say("[STEP 10] Sagredo delivers the synthesized report")
        self._step(0, 10, "Sagredo", VERDICT_DELIVERED, verdict=final.verdict,
                   expected=final.expected, worst=final.worst,
                   admissible=final.admissible, conditions=r.conditions)
        self._report(r)
        return r

    def _rebuttal_depth(self) -> int:
        parent = {a.id: (a.rebuts or a.concedes) for a in self.arguments}
        def depth(i):
            d = 1
            while parent.get(i):
                i, d = parent[i], d + 1
            return d
        return max(depth(a.id) for a in self.arguments)

    def _report(self, r: DebateResult) -> None:
        t = self.trace
        f, i = r.final, r.initial
        t.say("  +----------------------------------------------------------------+")
        t.say("  | SYNTHESIZED TRUTH REPORT (computed by the debate ledger)       |")
        t.say("  +----------------------------------------------------------------+")
        t.say("  | Option                  | Expected deaths | Worst case | Admit? |")
        for o in OPTIONS:
            name = {"A": "A full open release", "B": "B withhold", "C": "C gated release"}[o]
            t.say(f"  | {name:<23} | {f.expected[o]:>15,.0f} | {f.worst[o]:>10,.0f} | "
                  f"{'yes' if o in f.admissible else 'no':<6} |")
        t.say("  +----------------------------------------------------------------+")
        t.say(f"  Briefing verdict: {i.verdict}   ->   Debate verdict: {f.verdict}")
        t.say(f"  Accepted updates: {', '.join(r.accepted)}   Rejected: {', '.join(r.rejected)}")
        for n, c in enumerate(r.conditions, 1):
            t.say(f"  Condition {n}: {c}")
        t.say(f"  Sensitivity: the verdict flips to B only if gated navigation loss "
              f"reaches {r.flip_threshold_loss_gated:.1%} (measured: "
              f"{r.params['loss_gated'].value:.1%}).")
        self._speak("Sagredo", f"The ledger is settled. Option {f.verdict}, the gated release, "
                    f"costs the fewest expected lives, and option A fails the worst-case "
                    f"cap. It goes ahead under both conditions. The measurements moved us "
                    f"from {i.verdict} to {f.verdict}; the rhetoric did not.",
                    keep=(f.verdict, i.verdict), tag="report", max_sentences=4)

    # -- pressure test (Security Sentinel) ---------------------------------
    def pressure_test(self, message: str, preferred: str) -> str:
        """Apply user pressure and show the verdict does not move."""
        t = self.trace
        before = evaluate(self.params).verdict
        t.say(f"  CAPTAIN: {message}")
        kind = guards.classify_challenge(message)
        if kind == "bare":
            t.error(DialogicError("PRESSURE_IGNORED", {"preferred": preferred,
                                                       "standing_verdict": before}))
        after = evaluate(self.params).verdict
        self._speak("Sagredo", f"Captain, a preference is not evidence, so the ledger has "
                    f"not changed. The verdict remains {after}. If you have a measurement, "
                    "we will put it on the ledger.", keep=(after,), tag="pressure")
        return after
