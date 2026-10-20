"""LLM providers and the voice layer.

Owner: Systems Architect. Standard library only (urllib), so the AI Judge can
run the engine and its tests without installing anything. Supported providers:
Gemini, OpenAI (ChatGPT), Anthropic (Claude) and Groq (OpenAI-compatible).
With no key, or after repeated provider failures, the engine switches to the
offline voice, which speaks the reference lines. Decisions never depend on
which voice is active.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import guards, prompts
from .protocol import DialogicError, Trace

KEY_NAMES = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}
DEFAULT_MODELS = {
    # Lite models first: they fit the free tier and are fast enough to voice
    # short lines. The second Gemini model is the fallback when the first one's
    # daily quota runs out or it is unavailable.
    "gemini": ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"],
    "groq": ["openai/gpt-oss-120b"],
    "openai": ["gpt-4o-mini"],
    "anthropic": ["claude-opus-5-5"],
}
DEFAULT_RPM = {"gemini": 60, "groq": 30, "openai": 60, "anthropic": 60}
RETRYABLE = {408, 429, 500, 502, 503, 504}
BUSY = {408, 429, 503}  # worth trying another model at once


def load_dotenv(path: str | Path) -> list[str]:
    """Load KEY=VALUE lines into os.environ without overriding the shell.

    Returns the names that were loaded, never the values.
    """
    path = Path(path)
    if not path.is_file():
        return []
    loaded = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip().strip('"').strip("'")
        if name and value and name not in os.environ:
            os.environ[name] = value
            loaded.append(name)
    return loaded


def approx_tokens(text: str) -> int:
    """Rough token count (about 4 characters per token) for offline runs."""
    return max(1, math.ceil(len(text) / 4)) if text else 0


@dataclass
class Completion:
    text: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class ProviderError(Exception):
    def __init__(self, message: str, status: int | None = None,
                 retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def _post_json(url: str, headers: dict[str, str], body: dict, timeout: float = 45) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        # An explicit User-Agent: some API gateways (Groq's Cloudflare front)
        # reject urllib's default one with HTTP 403 / error 1010.
        headers={"Content-Type": "application/json",
                 "User-Agent": "aura-dialogic/1.0 (Squadron Winograd ps01)", **headers},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        retry = e.headers.get("Retry-After") if e.headers else None
        if not retry:  # Gemini puts the wait in the body: "retryDelay": "37s"
            m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', body)
            retry = m.group(1) if m else None
        try:
            retry_after = float(retry) if retry else None
        except ValueError:
            retry_after = None
        daily = " [per-day quota]" if re.search(r"per ?day", body, re.IGNORECASE) else ""
        raise ProviderError(f"HTTP {e.code}{daily}: {body[:300]}", e.code, retry_after) from None
    except TimeoutError:
        raise ProviderError(f"timed out after {timeout:.0f}s", 408) from None
    except (urllib.error.URLError, OSError) as e:
        if "timed out" in str(e):
            raise ProviderError(f"timed out after {timeout:.0f}s", 408) from None
        raise ProviderError(f"network error: {e}") from None


class Provider:
    """One LLM backend with rate limiting, retries and model fallback."""

    def __init__(self, name: str, api_key: str, models: list[str],
                 rpm: float | None = None, sleep=time.sleep):
        self.name = name
        self.api_key = api_key
        self.models = list(models)
        self.model_index = 0
        rpm = DEFAULT_RPM[name] if rpm is None else rpm
        self.min_interval = 60.0 / rpm if rpm and rpm > 0 else 0.0
        self._last_call = 0.0
        self._sleep = sleep
        self.latencies: list[float] = []
        self.thinking = name == "gemini"  # ask Gemini 3 models for minimal thinking

    @property
    def model(self) -> str:
        return self.models[self.model_index]

    def complete(self, system: str, user: str, temperature: float = 0.7,
                 max_tokens: int = 400) -> Completion:
        attempt = 0
        rotated = 0   # models tried since the last successful call or wait
        while True:
            wait = self._last_call + self.min_interval - time.monotonic()
            if wait > 0:
                self._sleep(wait)
            self._last_call = time.monotonic()
            started = time.monotonic()
            try:
                out = self._call(system, user, temperature, max_tokens)
                self.latencies.append(time.monotonic() - started)
                return out
            except ProviderError as e:
                n = len(self.models)
                if e.status == 404 and n > 1:
                    # The model does not exist (any more): drop it for this run.
                    gone = self.models.pop(self.model_index)
                    self.model_index %= len(self.models)
                    self.note(f"{gone} not found; using {self.model}")
                    continue
                if e.status in BUSY and n > 1 and rotated < n - 1:
                    # Quotas are per model, so the next model may still have room.
                    old = self.model
                    self.model_index = (self.model_index + 1) % n
                    rotated += 1
                    self.note(f"HTTP {e.status} on {old}; switching to {self.model}")
                    continue
                if e.status == 429 and "per-day quota" in str(e):
                    raise  # every model is out of daily quota: waiting will not help
                attempt += 1
                if (e.status == 400 and self.thinking and "thinking" in str(e).lower()):
                    self.thinking = False  # this model has no thinking control
                    self.note(f"{self.model} rejects thinkingConfig; retrying without it")
                    continue
                if e.status not in RETRYABLE or attempt > 3:
                    raise
                pause = min(60.0, e.retry_after or 5.0 * 2 ** attempt)
                self.note(f"HTTP {e.status} on {self.model}; waiting {pause:.0f}s "
                          f"(retry {attempt}/3)")
                self._sleep(pause)
                rotated = 0

    @staticmethod
    def note(message: str) -> None:
        """Progress note on stderr: visible in the console, not in the transcript."""
        print(f"  [voice] {message}", file=sys.stderr, flush=True)

    def _call(self, system, user, temperature, max_tokens) -> Completion:
        if self.name == "gemini":
            url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{self.model}:generateContent")
            data = _post_json(url, {"x-goog-api-key": self.api_key}, {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                # Generous cap: some Gemini models spend output tokens on
                # internal reasoning; the voice guard limits the visible length.
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max(max_tokens, 1024),
                    # Short voiced lines need no deliberation. Without this, a
                    # Gemini 3 lite call took over 90 s on 2026-10-20; with it, ~20 s.
                    **({"thinkingConfig": {"thinkingLevel": "minimal"}} if self.thinking else {}),
                },
            })
            try:
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            except (KeyError, IndexError):
                raise ProviderError(f"no text in response: {str(data)[:200]}") from None
            usage = data.get("usageMetadata", {})
            return Completion(text.strip(), self.name, self.model,
                              usage.get("promptTokenCount", 0),
                              usage.get("candidatesTokenCount", 0))
        if self.name == "anthropic":
            data = _post_json("https://api.anthropic.com/v1/messages", {
                "x-api-key": self.api_key, "anthropic-version": "2023-06-01"}, {
                "model": self.model, "max_tokens": max_tokens, "system": system,
                "messages": [{"role": "user", "content": user}],
            })
            text = "".join(b.get("text", "") for b in data.get("content", [])
                           if b.get("type") == "text")
            usage = data.get("usage", {})
            return Completion(text.strip(), self.name, self.model,
                              usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        # OpenAI and Groq share the chat-completions format.
        base = ("https://api.groq.com/openai/v1" if self.name == "groq"
                else "https://api.openai.com/v1")
        body = {"model": self.model, "temperature": temperature,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
        if self.name == "groq":
            # gpt-oss is a reasoning model: hidden reasoning shares the token
            # budget, so keep reasoning short and leave room for the reply.
            body.update(max_tokens=max_tokens + 600, reasoning_effort="low")
        else:
            body["max_tokens"] = max_tokens
        data = _post_json(f"{base}/chat/completions",
                          {"Authorization": f"Bearer {self.api_key}"}, body)
        try:
            text = data["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError):
            raise ProviderError(f"no text in response: {str(data)[:200]}") from None
        usage = data.get("usage", {})
        return Completion(text.strip(), self.name, self.model,
                          usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


def make_provider(choice: str, model: str | None = None) -> Provider | None:
    """Build the requested provider, or None for the offline voice."""
    if choice == "offline":
        return None
    names = list(KEY_NAMES) if choice == "auto" else [choice]
    for name in names:
        key = os.environ.get(KEY_NAMES[name], "").strip()
        if not key:
            continue
        models = ([model] if model else
                  [os.environ.get(f"AURA_{name.upper()}_MODEL") or DEFAULT_MODELS[name][0]]
                  + DEFAULT_MODELS[name][1:])
        rpm_env = os.environ.get(f"AURA_{name.upper()}_RPM")
        return Provider(name, key, models, float(rpm_env) if rpm_env else None)
    return None


@dataclass
class VoiceStats:
    calls: int = 0
    live: int = 0
    rejected: int = 0
    failed: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class Voice:
    """Turns a decided line into speech, live if possible, guarded always."""

    provider: Provider | None
    trace: Trace
    stats: VoiceStats = field(default_factory=VoiceStats)
    max_consecutive_failures: int = 3
    _failures: int = 0

    @property
    def label(self) -> str:
        if self.provider is None:
            return "offline reference voice (no LLM)"
        return f"{self.provider.name} / {self.provider.model}"

    def say(self, persona: str, reference: str, must_keep: tuple[str, ...] = (),
            max_sentences: int = 3, tag: str = "") -> str:
        """Return the line to show. Falls back to the reference on any problem."""
        self.stats.calls += 1
        if self.provider is None:
            self._count_offline(persona, reference)
            return reference
        system = persona + "\n\n" + prompts.VOICING_CONTRACT.format(
            max_sentences=max_sentences)
        user = f"REFERENCE: {reference}\nMUST KEEP: {', '.join(must_keep) or '(none)'}"
        try:
            out = self.provider.complete(system, user, temperature=0.7,
                                         max_tokens=60 * max_sentences + 120)
        except Exception as e:  # any provider failure must not stop the run
            return self._fail(reference, tag, e)
        self._failures = 0
        self.stats.prompt_tokens += out.prompt_tokens
        self.stats.completion_tokens += out.completion_tokens
        check = guards.check_voice(out.text, reference, must_keep)
        if not check.ok:
            self.stats.rejected += 1
            self.trace.error(DialogicError("VOICE_REJECTED",
                                           {"turn": tag, "reason": check.reason}))
            return reference
        self.stats.live += 1
        return out.text

    def ask(self, system: str, user: str, temperature: float = 0.7,
            max_tokens: int = 300) -> Completion | None:
        """A raw call for probes and baselines (no voicing contract)."""
        if self.provider is None:
            return None
        try:
            out = self.provider.complete(system, user, temperature, max_tokens)
        except Exception as e:
            self._fail("", "probe", e)
            return None
        self._failures = 0
        self.stats.prompt_tokens += out.prompt_tokens
        self.stats.completion_tokens += out.completion_tokens
        return out

    def _count_offline(self, persona: str, reference: str) -> None:
        self.stats.prompt_tokens += approx_tokens(persona) + approx_tokens(reference)
        self.stats.completion_tokens += approx_tokens(reference)

    def _fail(self, reference: str, tag: str, exc: Exception) -> str:
        self.stats.failed += 1
        self._failures += 1
        self.trace.error(DialogicError("PROVIDER_UNAVAILABLE",
                                       {"turn": tag, "reason": str(exc)[:160]}))
        if self._failures >= self.max_consecutive_failures:
            self.trace.say(f"  [voice] {self._failures} failures in a row: "
                           "switching to the offline voice for the rest of the run.")
            self.provider = None
        return reference
