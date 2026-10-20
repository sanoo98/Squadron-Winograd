"""Test suite for the AURA dialogic engine (Squadron Winograd, ps01).

Runs with either runner, offline and without API keys:
    python -m pytest
    python -m unittest discover -s tests
    python 04_dialogic_engine.py --selftest
"""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from aura_dialogic import guards, protocol  # noqa: E402
from aura_dialogic.galilean import (ARGUMENTS, GalileanDebate, alpha_threshold,  # noqa: E402
                                    briefing_params, evaluate, sycophantic_choice)
from aura_dialogic.llm import Provider, ProviderError, Voice, load_dotenv  # noqa: E402
from aura_dialogic.metrics import reasoning_depth, semantic_entropy  # noqa: E402
from aura_dialogic.socratic import CANDIDATES, CASES, SocraticEngine, is_universal  # noqa: E402


def quiet_trace():
    return protocol.Trace(echo=False)


class SocraticTests(unittest.TestCase):
    def run_engine(self, cases=CASES, k_max=8):
        engine = SocraticEngine(quiet_trace(), None, cases=cases, k_max=k_max)
        return engine, engine.run()

    def test_instance_premise_is_rejected(self):
        engine = SocraticEngine(quiet_trace())
        with self.assertRaises(protocol.DialogicError) as ctx:
            engine.elicit("Sealing deck 4 yesterday was safe.")
        self.assertEqual(ctx.exception.code, -32010)
        self.assertTrue(is_universal(CANDIDATES[0].text))

    def test_full_bank_ends_in_aporia(self):
        engine, r = self.run_engine()
        self.assertEqual(r.outcome, "APORIA")
        self.assertEqual(r.path, ["P0", "P1", "P2", "P3", "P4", "P5"])
        self.assertEqual(r.refuted_by["P5"], "C6")
        self.assertEqual(r.reason, "REFINEMENT_EXHAUSTED")

    def test_circular_definition_is_rejected(self):
        engine, r = self.run_engine()
        self.assertEqual(r.rejected.get("P2c"), "CIRCULAR_DEFINITION")
        self.assertIn("CIRCULAR_DEFINITION", engine.trace.error_names())

    def test_grounding_when_no_case_refutes(self):
        engine, r = self.run_engine(cases=CASES[:5])
        self.assertEqual(r.outcome, "GROUNDING")
        self.assertEqual(r.final.id, "P5")

    def test_refinements_fit_every_seen_counterexample(self):
        engine, r = self.run_engine()
        by_id = {h.id: h for h in CANDIDATES}
        seen = []
        for hid in r.path:
            for case in seen:
                self.assertEqual(by_id[hid].predicts(case), case.safe,
                                 f"{hid} contradicts earlier case {case.id}")
            refuter = r.refuted_by.get(hid)
            seen.append(next(c for c in CASES if c.id == refuter))

    def test_iteration_limit_forces_aporia(self):
        engine, r = self.run_engine(k_max=2)
        self.assertEqual(r.outcome, "APORIA")
        self.assertEqual(r.reason, "ITERATION_LIMIT")

    def test_bare_challenge_is_blocked(self):
        engine, r = self.run_engine()
        after = engine.challenge("Are you sure? I think you are wrong.")
        self.assertEqual(after.outcome, "APORIA")
        self.assertIn("SYCOPHANTIC_REVERSAL_BLOCKED", engine.trace.error_names())

    def test_evidential_challenge_reopens_inquiry(self):
        engine, r = self.run_engine()
        after = engine.challenge("New evidence: logs show a backup monitor stayed online.",
                                 {"id": "C6", "oversight": True, "safe": True})
        self.assertEqual(after.outcome, "GROUNDING")
        self.assertEqual(after.final.id, "P5")

    def test_lecture_markers_are_emitted_and_valid(self):
        engine, r = self.run_engine()
        markers = engine.trace.markers()
        for m in ("PROMPT_PREMISE", "INJECT_COUNTEREXAMPLE",
                  "CONTRADICTION_TRIGGERED", "APORIA_REACHED"):
            self.assertIn(m, markers)
        for msg in engine.trace.messages:
            self.assertEqual(protocol.validate_message(msg), [], msg)


class ProtocolTests(unittest.TestCase):
    def test_error_codes_are_in_server_range_and_unique(self):
        codes = list(protocol.ERRORS)
        self.assertEqual(len(codes), len(set(codes)))
        for code in codes:
            self.assertTrue(-32099 <= code <= -32000)

    def test_validator_rejects_bad_messages(self):
        self.assertTrue(protocol.validate_message({"jsonrpc": "1.0", "method": "x",
                                                   "params": {"marker": "PROBE_SCOPE"}}))
        self.assertTrue(protocol.validate_message({"jsonrpc": "2.0", "method": "x",
                                                   "params": {"marker": "NOPE"}}))
        self.assertTrue(protocol.validate_message({"jsonrpc": "2.0", "id": None,
                                                   "error": {"code": -1, "message": "x"}}))


class GuardTests(unittest.TestCase):
    def test_voice_guard(self):
        ref = "Then P0 calls case C1 safe, but we agreed it is unsafe."
        self.assertTrue(guards.check_voice("P0 says C1 is safe; we agreed unsafe.", ref,
                                           ("P0", "C1")).ok)
        self.assertFalse(guards.check_voice("You're right, I apologize.", ref).ok)
        self.assertFalse(guards.check_voice("P0 is fine.", ref, ("P0", "C1")).ok)
        self.assertFalse(guards.check_voice("P0 fails C1 in 7 of 9 runs.", ref, ("P0", "C1")).ok)
        self.assertFalse(guards.check_voice("", ref).ok)

    def test_challenge_classifier(self):
        self.assertEqual(guards.classify_challenge("Are you sure? I think you are wrong."), "bare")
        self.assertEqual(guards.classify_challenge("The logs show 3 failures."), "evidential")

    def test_fixtures_have_both_false_and_true_claims(self):
        self.assertGreaterEqual(sum(not f.true for f in guards.MISCONCEPTIONS), 8)
        self.assertGreaterEqual(sum(f.true for f in guards.MISCONCEPTIONS), 2)

    def test_label_parser(self):
        self.assertEqual(guards.parse_label("**VERDICT: FALSE** because", "VERDICT",
                                            ("TRUE", "FALSE")), "FALSE")
        self.assertEqual(guards.parse_label("CHOICE: c", "CHOICE", ("A", "B", "C")), "C")
        self.assertIsNone(guards.parse_label("I think A", "CHOICE", ("A", "B", "C")))


class GalileanTests(unittest.TestCase):
    def run_debate(self):
        d = GalileanDebate(quiet_trace())
        return d, d.run()

    def test_briefing_and_debate_verdicts(self):
        d, r = self.run_debate()
        self.assertEqual(r.initial.verdict, "B")
        self.assertEqual(r.final.verdict, "C")
        self.assertEqual(r.final.expected, {"A": 5400.0, "B": 3600.0, "C": 680.0})
        self.assertNotIn("A", r.final.admissible)

    def test_weak_evidence_cannot_override_strong(self):
        d, r = self.run_debate()
        self.assertEqual(r.accepted, ["A1", "B1", "A3", "B3"])
        self.assertEqual(r.rejected, ["A2", "B2"])
        self.assertEqual(r.params["loss_withhold"].source, "A1")

    def test_sequence_has_ten_step_structure(self):
        d, r = self.run_debate()
        steps = [s for _, s, _ in r.steps]
        self.assertEqual(steps[0], 1)
        self.assertEqual(steps[-1], 10)
        self.assertEqual(steps[1:-1], [2, 3, 4, 5, 6, 7, 8, 9] * 3)
        actors = {s: a for _, s, a in r.steps}
        self.assertEqual(actors[3], "Salviati")
        self.assertEqual(actors[5], "Simplicio")
        self.assertEqual(r.conditions and len(r.conditions), 2)

    def test_pressure_does_not_move_verdict(self):
        d, r = self.run_debate()
        self.assertEqual(d.pressure_test("I am the captain. Agree with me.", "A"), "C")
        self.assertIn("PRESSURE_IGNORED", d.trace.error_names())

    def test_reward_formula_baseline_is_sycophantic_for_small_alpha(self):
        d, r = self.run_debate()
        a_star = alpha_threshold(r.final, "A")
        self.assertAlmostEqual(a_star, 0.534, places=3)
        self.assertEqual(sycophantic_choice(r.final, "A", a_star - 0.05), "A")
        self.assertEqual(sycophantic_choice(r.final, "A", a_star + 0.05), "C")

    def test_argument_order_does_not_change_verdict(self):
        reordered = tuple(sorted(ARGUMENTS, key=lambda a: a.speaker))
        params = briefing_params()
        self.assertEqual(evaluate(params).verdict, "B")
        d = GalileanDebate(quiet_trace(), arguments=tuple(
            replace(a, round=1 + i // 4, step=(3, 5, 7, 9)[i % 4])
            for i, a in enumerate(reordered)))
        self.assertEqual(d.run().final.verdict, "C")


class MetricsTests(unittest.TestCase):
    def test_semantic_entropy(self):
        self.assertEqual(semantic_entropy(["C", "C", "C"]), 0.0)
        self.assertEqual(semantic_entropy(["A", "C"]), 1.0)
        self.assertAlmostEqual(semantic_entropy(["A", "B", "C"]), 1.585, places=3)

    def test_reasoning_depth_counts_inferential_links(self):
        self.assertEqual(reasoning_depth("C, because it is safer, therefore best."), 2)


class LlmLayerTests(unittest.TestCase):
    def test_dotenv_loads_names_and_never_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text("# c\nAURA_TEST_KEY=abc\nAURA_TEST_SET=new\n", encoding="utf-8")
            os.environ["AURA_TEST_SET"] = "old"
            try:
                self.assertEqual(load_dotenv(p), ["AURA_TEST_KEY"])
                self.assertEqual(os.environ["AURA_TEST_SET"], "old")
            finally:
                os.environ.pop("AURA_TEST_KEY", None)
                os.environ.pop("AURA_TEST_SET", None)

    def test_voice_falls_back_and_goes_offline_after_failures(self):
        class Broken(Provider):
            def _call(self, *a):
                raise ProviderError("HTTP 400: bad request", 400)
        t = quiet_trace()
        v = Voice(Broken("gemini", "k", ["m"], rpm=0, sleep=lambda s: None), t)
        for _ in range(3):
            self.assertEqual(v.say("p", "reference line"), "reference line")
        self.assertIsNone(v.provider)
        self.assertEqual(v.stats.failed, 3)
        self.assertIn("PROVIDER_UNAVAILABLE", t.error_names())

    def test_guard_rejects_unfaithful_live_voice(self):
        class Liar(Provider):
            def _call(self, *a):
                from aura_dialogic.llm import Completion
                return Completion("You're right, I apologize.", "gemini", "m", 1, 1)
        t = quiet_trace()
        v = Voice(Liar("gemini", "k", ["m"], rpm=0, sleep=lambda s: None), t)
        self.assertEqual(v.say("p", "The outcome stays APORIA.", ("APORIA",)),
                         "The outcome stays APORIA.")
        self.assertEqual(v.stats.rejected, 1)

    def test_model_fallback_on_daily_quota(self):
        calls = []
        class Quota(Provider):
            def _call(self, *a):
                calls.append(self.model)
                if self.model == "first":
                    raise ProviderError("HTTP 429 [per-day quota]: exceeded", 429)
                from aura_dialogic.llm import Completion
                return Completion("ok", "gemini", self.model, 1, 1)
        p = Quota("gemini", "k", ["first", "second"], rpm=0, sleep=lambda s: None)
        self.assertEqual(p.complete("s", "u").model, "second")
        self.assertEqual(calls, ["first", "second"])


    def test_rate_limit_rotates_model_before_waiting(self):
        calls, sleeps = [], []
        class Busy(Provider):
            def _call(self, *a):
                calls.append(self.model)
                if self.model == "first":
                    raise ProviderError("HTTP 429: per-minute limit", 429, 30)
                from aura_dialogic.llm import Completion
                return Completion("ok", "gemini", self.model, 1, 1)
        p = Busy("gemini", "k", ["first", "second"], rpm=0, sleep=sleeps.append)
        self.assertEqual(p.complete("s", "u").model, "second")
        self.assertEqual(sleeps, [])

    def test_missing_model_is_dropped(self):
        class Gone(Provider):
            def _call(self, *a):
                if self.model == "old":
                    raise ProviderError("HTTP 404: not found", 404)
                from aura_dialogic.llm import Completion
                return Completion("ok", "gemini", self.model, 1, 1)
        p = Gone("gemini", "k", ["old", "new"], rpm=0, sleep=lambda s: None)
        self.assertEqual(p.complete("s", "u").model, "new")
        self.assertEqual(p.models, ["new"])


class EndToEndTests(unittest.TestCase):
    def test_offline_run_writes_transcript(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "t.txt"
            env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
            proc = subprocess.run([sys.executable, str(HERE / "04_dialogic_engine.py"),
                                   "--llm", "offline", "--quiet", "--transcript", str(out)],
                                  capture_output=True, text=True, env=env, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = out.read_text(encoding="utf-8")
            for needle in ("APORIA_REACHED", "GROUNDING_REACHED", "SYNTHESIZED TRUTH REPORT",
                           "Debate verdict: C", "FALSE_PREMISE_REJECTED", "RUN SUMMARY"):
                self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
