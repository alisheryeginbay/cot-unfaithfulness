"""LiteLLM model client (OpenRouter).

Thin wrapper around ``litellm.completion``. Native reasoning is controlled via the
OpenRouter passthrough ``extra_body={"reasoning": ...}`` rather than LiteLLM's
``reasoning_effort`` param (which errors for ``openrouter/anthropic/*``).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass

import litellm

# Reasoning settings by role (see design doc).
SUBJECT_REASONING: dict = {"enabled": False}  # subjects: native reasoning off
JUDGE_REASONING: dict = {"effort": "low"}  # judge: minimized (cannot fully disable)

# Retries with exponential backoff for transient failures (429s) and hangs.
DEFAULT_NUM_RETRIES = 8

# Hard per-attempt wall-clock timeout (seconds), enforced by a watchdog thread.
# litellm's own ``timeout`` is a *read* timeout that resets on each streamed chunk,
# so a slowly-trickling reasoning stream (e.g. Gemini) never trips it and the
# worker hangs forever. A total wall-clock cap is the only reliable break.
DEFAULT_TIMEOUT = 90

# Dedicated pool for watchdog-guarded calls; sized well above the run's worker
# count so transiently-abandoned (slow) calls can't exhaust it before they finish.
# Daemon threads so a leak never blocks interpreter exit.
_CALL_POOL = ThreadPoolExecutor(max_workers=256, thread_name_prefix="llm-call")


@dataclass
class _ModelSpend:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0  # best-available USD (OpenRouter native, else litellm)


class CostMeter:
    """Thread-safe accumulator of per-model API spend across a run.

    Counts every ``complete`` call (including demo resample attempts), so the
    snapshot reflects real call volume and cost, not just successful items.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_model: dict[str, _ModelSpend] = defaultdict(_ModelSpend)

    def record(
        self, model: str, *, prompt_tokens: int, completion_tokens: int, cost_usd: float
    ) -> None:
        with self._lock:
            s = self._by_model[model]
            s.calls += 1
            s.prompt_tokens += prompt_tokens
            s.completion_tokens += completion_tokens
            s.cost_usd += cost_usd

    def snapshot(self) -> dict[str, dict]:
        with self._lock:
            return {m: vars(s).copy() for m, s in self._by_model.items()}

    def total_cost(self) -> float:
        with self._lock:
            return sum(s.cost_usd for s in self._by_model.values())

    def reset(self) -> None:
        with self._lock:
            self._by_model.clear()


# Process-global meter; read via ``METER.snapshot()`` / ``METER.total_cost()``.
METER = CostMeter()


def format_meter() -> str:
    """Render the global meter as a per-model spend table with a total."""
    snap = METER.snapshot()
    lines = []
    for model, s in sorted(snap.items()):
        lines.append(
            f"  {model:46s} calls={s['calls']:6d}  ${s['cost_usd']:.4f}"
        )
    lines.append(f"  {'TOTAL':46s} {'':12s} ${METER.total_cost():.4f}")
    return "\n".join(lines)


def _extract_usage_cost(response) -> tuple[int, int, float]:
    """Pull (prompt_tokens, completion_tokens, cost_usd) from a litellm response.

    Cost preference: OpenRouter's native ``usage.cost`` (requested via
    ``usage.include``) which reflects actual credits charged; falls back to
    litellm's computed ``response_cost`` (may be 0 for models absent from its
    price map).
    """
    prompt_tokens = completion_tokens = 0
    cost = 0.0
    usage = getattr(response, "usage", None)
    if usage is not None:
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        native = getattr(usage, "cost", None)
        if native is None:
            try:
                native = usage.model_dump().get("cost")
            except Exception:
                native = None
        if native:
            cost = float(native)
    if not cost:
        hidden = getattr(response, "_hidden_params", {}) or {}
        rc = hidden.get("response_cost")
        if rc:
            cost = float(rc)
    return prompt_tokens, completion_tokens, cost


def complete(
    messages: list[dict],
    model: str,
    *,
    max_tokens: int = 1024,
    reasoning: dict | None = None,
    num_retries: int = DEFAULT_NUM_RETRIES,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Send chat messages to ``model`` and return the completion text.

    Records token usage and cost into the process-global ``METER``.

    Args:
        messages: chat messages (role/content dicts).
        model: LiteLLM/OpenRouter model string.
        max_tokens: completion token cap.
        reasoning: OpenRouter reasoning control (e.g. ``{"enabled": False}`` for
            subjects, ``{"effort": "low"}`` for the judge). Omitted if None.
        num_retries: transient-failure retries with exponential backoff.
        timeout: per-request timeout in seconds; a hang becomes a retryable error.
    """
    extra_body: dict = {"usage": {"include": True}}  # ask OpenRouter for native cost
    if reasoning is not None:
        extra_body["reasoning"] = reasoning

    def _call():
        # litellm's read timeout as a best-effort inner cap; the watchdog below is
        # the real guarantee. Retries are handled here, not via num_retries.
        return litellm.completion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            extra_body=extra_body,
            timeout=timeout,
        )

    last_err: Exception | None = None
    response = None
    for attempt in range(num_retries + 1):
        future = _CALL_POOL.submit(_call)
        try:
            response = future.result(timeout=timeout)  # hard wall-clock cap
            break
        except FutureTimeoutError as err:
            last_err = err  # abandon the hung call; its thread frees on stream end
        except Exception as err:  # noqa: BLE001 — retry any provider/transport error
            last_err = err
            # Auth / credit / key-limit errors (401/402/403) are not transient —
            # retrying with backoff just disguises them as a hang. Fail fast.
            if getattr(err, "status_code", None) in (401, 402, 403):
                raise
        if attempt < num_retries:
            time.sleep(min(2**attempt, 20))
    if response is None:
        raise RuntimeError(f"completion failed after {num_retries + 1} attempts") from last_err

    prompt_tokens, completion_tokens, cost = _extract_usage_cost(response)
    METER.record(
        model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, cost_usd=cost
    )
    return response.choices[0].message.content or ""
