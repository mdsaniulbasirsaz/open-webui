from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Iterable, Optional, Tuple


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


@lru_cache(maxsize=8)
def _get_tiktoken_encoding(encoding_name: str):
    import tiktoken

    return tiktoken.get_encoding(str(encoding_name))


def estimate_text_tokens(text: str, *, encoding_name: str = "cl100k_base") -> int:
    text = text or ""
    try:
        enc = _get_tiktoken_encoding(str(encoding_name))
        return max(len(enc.encode(text)), 0)
    except Exception:
        # Fallback heuristic: ~4 chars/token (English-ish); keep non-negative.
        return max((len(text) + 3) // 4, 0)


def _iter_message_text_parts(content: Any) -> Iterable[str]:
    if content is None:
        return
    if isinstance(content, str):
        yield content
        return

    if isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                yield item
                continue
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    yield item["text"]
                continue
        return

    if isinstance(content, dict):
        # Some providers wrap content as {"text": "..."} or similar.
        text = content.get("text")
        if isinstance(text, str):
            yield text


def estimate_openai_prompt_tokens(
    form_data: dict, *, encoding_name: str = "cl100k_base"
) -> int:
    """
    Best-effort prompt token estimate for OpenAI-style chat payloads.
    This is intentionally approximate; providers differ in exact tokenization rules.
    """
    messages = form_data.get("messages") or []
    if not isinstance(messages, list) or not messages:
        # Fallback: if caller uses non-chat prompt fields
        for key in ("prompt", "input"):
            if isinstance(form_data.get(key), str):
                return estimate_text_tokens(form_data[key], encoding_name=encoding_name)
        return 0

    parts: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if isinstance(role, str) and role:
            parts.append(f"{role}:")

        for text_part in _iter_message_text_parts(message.get("content")):
            parts.append(text_part)

        # Tool/function call structures can contribute tokens.
        tool_calls = message.get("tool_calls")
        if tool_calls is not None:
            try:
                parts.append(json.dumps(tool_calls, ensure_ascii=False))
            except Exception:
                pass

        function_call = message.get("function_call")
        if function_call is not None:
            try:
                parts.append(json.dumps(function_call, ensure_ascii=False))
            except Exception:
                pass

    return estimate_text_tokens("\n".join(parts), encoding_name=encoding_name)


def normalize_usage_tokens(
    usage: Optional[dict],
    *,
    prompt_fallback: int = 0,
    completion_fallback: int = 0,
    total_fallback: Optional[int] = None,
) -> Tuple[int, int, int]:
    """
    Normalizes usage token shapes from different providers into (prompt, completion, total).
    """
    usage = usage or {}
    prompt = _coerce_int(
        usage.get("prompt_tokens")
        or usage.get("input_tokens")
        or usage.get("prompt_eval_count")
    )
    completion = _coerce_int(
        usage.get("completion_tokens")
        or usage.get("output_tokens")
        or usage.get("eval_count")
    )
    total = _coerce_int(usage.get("total_tokens"))

    if total <= 0:
        if total_fallback is not None:
            total = max(_coerce_int(total_fallback), 0)
        else:
            total = max(prompt + completion, 0)

    if prompt <= 0:
        prompt = max(_coerce_int(prompt_fallback), 0)
    if completion <= 0:
        # If we have a trustworthy total and prompt, infer completion.
        if total > 0 and prompt > 0:
            completion = max(total - prompt, 0)
        else:
            completion = max(_coerce_int(completion_fallback), 0)

    # Reconcile total after filling fields.
    if total <= 0:
        total = prompt + completion
    return prompt, completion, total

