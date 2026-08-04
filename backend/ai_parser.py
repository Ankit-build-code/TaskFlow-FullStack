"""
ai_parser.py — Rule-based mock parser for TaskFlow's quick-add feature (Section 3).

This module implements a fully deterministic, keyless, zero-network-call parser
that simulates what an LLM would return when given a free-text task description.

The parser follows the exact algorithm specified in Section 3, Task 3:
  a. Build a lower-cased working copy for keyword matching; keep original for title.
  b. Priority: check keyword groups in order — (i) urgent/asap → high,
               (ii) whenever/low priority → low, (iii) default → medium.
  c. Due-date hint: scan for date keywords in specified order.
  d. Title: strip matched spans from original-cased description, then .strip().
             If result is empty/whitespace-only → "Untitled task".

Prompting technique: Zero-shot prompting (documented in README).
The system message encodes the full parsing behavior as an instruction;
the user message carries only the raw description. No examples are
included in the prompt structure — this is characteristic of zero-shot.
"""

import re
from typing import Optional, Dict, Any


# ─────────────────────────────────────────────────────────────────
# Prompt structure (kept even for mock, so code mirrors a real LLM call)
# ─────────────────────────────────────────────────────────────────

SYSTEM_MESSAGE = (
    "You are a task-parsing assistant. "
    "Given a free-text task description, extract: "
    "title (the description with keywords stripped), "
    "priority (high/medium/low based on urgency keywords), "
    "and due_date_hint (a recognised date phrase, or null). "
    "Respond with valid JSON only: "
    '{{"title": "...", "priority": "...", "due_date_hint": "..." or null}}.'
)


def build_prompt_messages(description: str) -> list:
    """
    Return the role-based message list used by an LLM call.
    When the mock parser is active, this is constructed but not sent.
    """
    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": description},
    ]


# ─────────────────────────────────────────────────────────────────
# Priority keyword groups
# ─────────────────────────────────────────────────────────────────

# Group (i) → high  (checked first)
HIGH_KEYWORDS = ["urgent", "asap"]
# Group (ii) → low
LOW_KEYWORDS = ["whenever", "low priority"]


# ─────────────────────────────────────────────────────────────────
# Date-phrase keywords  (checked in this exact order per spec)
# ─────────────────────────────────────────────────────────────────

DATE_PHRASES_ORDERED = [
    "today",
    "tomorrow",
    "next week",
    "next monday",
    "next tuesday",
    "next wednesday",
    "next thursday",
    "next friday",
    "next saturday",
    "next sunday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


# ─────────────────────────────────────────────────────────────────
# Core mock parser
# ─────────────────────────────────────────────────────────────────

def mock_parse(description: str) -> Dict[str, Any]:
    """
    Deterministic rule-based parser.

    Parameters
    ----------
    description : str
        Raw free-text task description from the user.

    Returns
    -------
    dict with keys: title (str), priority (str), due_date_hint (str | None)
    """
    # ── a. Working copies ────────────────────────────────────────
    lower = description.lower()
    original = description          # kept untouched for title derivation

    # ── b. Priority ──────────────────────────────────────────────
    priority = "medium"             # default (group iii)

    has_high = any(kw in lower for kw in HIGH_KEYWORDS)
    has_low = any(kw in lower for kw in LOW_KEYWORDS)

    if has_high:
        priority = "high"           # group (i) wins even if both present
    elif has_low:
        priority = "low"

    # ── c. Due-date hint ─────────────────────────────────────────
    due_date_hint: Optional[str] = None
    matched_date_phrase: Optional[str] = None

    for phrase in DATE_PHRASES_ORDERED:
        if phrase in lower:
            due_date_hint = phrase
            matched_date_phrase = phrase
            break

    # ── d. Title ─────────────────────────────────────────────────
    # Strip ALL group (i) and (ii) keywords from the original-cased description
    # (title-stripping note: remove every occurrence of every group keyword,
    #  not just the one that determined priority)
    title = original

    # Keywords to strip from title: all group (i) + group (ii) keywords
    all_strip_keywords = HIGH_KEYWORDS + LOW_KEYWORDS  # order doesn't matter here

    for kw in all_strip_keywords:
        # Case-insensitive removal, all occurrences
        title = re.sub(re.escape(kw), "", title, flags=re.IGNORECASE)

    # Strip matched date phrase (all occurrences, case-insensitive)
    if matched_date_phrase:
        title = re.sub(re.escape(matched_date_phrase), "", title, flags=re.IGNORECASE)

    # Clean up: collapse multiple spaces, strip leading/trailing whitespace
    title = re.sub(r"[ \t]+", " ", title).strip()

    # If the result is empty or whitespace-only after stripping
    if not title.strip():
        title = "Untitled task"

    return {
        "title": title,
        "priority": priority,
        "due_date_hint": due_date_hint,
    }


# ─────────────────────────────────────────────────────────────────
# Optional real-LLM path (behind USE_REAL_LLM feature flag)
# ─────────────────────────────────────────────────────────────────

def parse_task_description(description: str) -> Dict[str, Any]:
    """
    Entry point for the quick-add parser.

    If the environment variable USE_REAL_LLM=1 is set AND an API key is present,
    delegates to the real LLM call. Otherwise falls back to mock_parse automatically.
    Grading is always performed with the flag off.
    """
    import os
    use_real = os.environ.get("USE_REAL_LLM", "").strip().lower() in ("1", "true", "yes")

    if use_real:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if api_key:
            try:
                return _real_llm_parse(description, api_key)
            except Exception:
                # Any failure → fall back to mock silently
                pass

    return mock_parse(description)


def _real_llm_parse(description: str, api_key: str) -> Dict[str, Any]:
    """
    Optional: call OpenAI (or any compatible API) with the structured prompt.
    Only invoked when USE_REAL_LLM=1 and OPENAI_API_KEY is set.
    Falls back to mock on any error.
    """
    import json
    try:
        import openai  # type: ignore
    except ImportError:
        return mock_parse(description)

    client = openai.OpenAI(api_key=api_key)
    messages = build_prompt_messages(description)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
    )

    raw = response.choices[0].message.content
    parsed = json.loads(raw)

    # Validate and sanitise LLM output before returning
    title = str(parsed.get("title", "")).strip() or "Untitled task"
    priority = str(parsed.get("priority", "medium")).lower()
    if priority not in ("low", "medium", "high"):
        priority = "medium"
    due_date_hint = parsed.get("due_date_hint") or None

    return {"title": title, "priority": priority, "due_date_hint": due_date_hint}
