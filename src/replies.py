"""Preference banner and CBT-informed peer reply template rendering."""

from __future__ import annotations

from typing import Any

# Preference labels
PREFERENCE_LABELS = {
    "listening": "Listening",
    "shared_experience": "Shared experience",
    "practical_ideas": "Practical ideas",
    "gentle_accountability": "Gentle accountability",
    "encouragement": "Encouragement",
}

# Preference banners (single-preference wording) — CBT-informed peer norms
PREFERENCE_BANNERS = {
    "listening": (
        "This person prefers validation and noticing (situation/feelings) rather than "
        "advice or reframes — peer support, not therapy."
    ),
    "shared_experience": (
        "This person would like peer perspective: similar moments and optional tiny "
        "coping examples, without being fixed."
    ),
    "practical_ideas": (
        "This person is open to one optional inch-sized idea (BA-lite or a gentler "
        "take on the facts) — suggestions only, not homework."
    ),
    "gentle_accountability": (
        "This person wants plan–do–review lite: one tiny chosen step and a soft "
        "later check-in, with no pressure."
    ),
    "encouragement": (
        "This person would appreciate self-compassion-style encouragement — "
        "affirm noticing/showing up, avoid toxic positivity."
    ),
}

# Short clauses for combined banners
PREFERENCE_CLAUSES = {
    "listening": "validation and noticing without advice unless asked",
    "shared_experience": "peer perspective and optional tiny coping examples",
    "practical_ideas": "one optional BA-lite or balanced-take suggestion",
    "gentle_accountability": "gentle plan–do–review without pressure",
    "encouragement": "self-compassion encouragement without toxic positivity",
}

# Fallback hints if templates.json has none
DEFAULT_HINTS = {
    "listening": "naming what feels heaviest without solving it yet",
    "shared_experience": "pausing to notice situation / thought / feeling before pushing on",
    "practical_ideas": "writing one next inch-sized step only",
    "gentle_accountability": "choosing one tiny step to revisit later",
    "encouragement": "treating noticing itself as a worthwhile step",
}

ALLOWED_PREFERENCES = set(PREFERENCE_LABELS.keys())


def normalize_preferences(preferences: list[str] | None) -> list[str]:
    """Dedupe while preserving order; default to listening."""
    cleaned: list[str] = []
    for pref in preferences or []:
        if pref in ALLOWED_PREFERENCES and pref not in cleaned:
            cleaned.append(pref)
    return cleaned or ["listening"]


def preference_banner(preferences: list[str] | None) -> dict[str, Any]:
    """Build a banner that reflects all selected preferences."""
    prefs = normalize_preferences(preferences)
    labels = [PREFERENCE_LABELS[p] for p in prefs]

    if len(prefs) == 1:
        pref = prefs[0]
        message = PREFERENCE_BANNERS[pref]
    else:
        label_list = " and ".join(labels) if len(labels) == 2 else (
            ", ".join(labels[:-1]) + f", and {labels[-1]}"
        )
        clauses = [PREFERENCE_CLAUSES[p] for p in prefs]
        if len(clauses) == 2:
            joined = f"{clauses[0]}; also {clauses[1]}"
        else:
            joined = "; ".join(clauses[:-1]) + f"; and {clauses[-1]}"
        message = (
            f"This person prefers {label_list} (CBT-informed peer norms). "
            f"When responding, offer {joined}."
        )

    return {
        "preferences": prefs,
        "preference": prefs[0],  # primary / first listed
        "labels": labels,
        "label": " + ".join(labels),
        "message": message,
        "framing": "cbt_informed_peer_support_not_therapy",
    }


def select_reply_specs(
    preferences: list[str] | None,
    templates: dict[str, list[str]],
    *,
    count: int,
) -> list[tuple[str, str]]:
    """
    Pick (preference, template) pairs covering all selected preferences.

    Rotates across preferences so a dual choice like listening + encouragement
    yields replies from both pools when count > 1.
    """
    prefs = normalize_preferences(preferences)
    count = max(1, count)
    specs: list[tuple[str, str]] = []

    # Round-robin across preferences, then across templates within each
    cursors = {p: 0 for p in prefs}
    for i in range(count):
        pref = prefs[i % len(prefs)]
        pool = list(templates.get(pref) or templates.get("listening") or [])
        if not pool:
            pool = ["I'm here with you."]
        idx = cursors[pref] % len(pool)
        cursors[pref] += 1
        specs.append((pref, pool[idx]))
    return specs


def render_template(
    template: str,
    *,
    summary: str,
    preference: str,
    hints: dict[str, str] | None = None,
) -> str:
    hint_map = {**DEFAULT_HINTS, **(hints or {})}
    hint = hint_map.get(preference, DEFAULT_HINTS["listening"])
    short = summary.strip()
    # Prefer a compact paraphrase-friendly clip for listening templates
    if len(short) > 72:
        short = short[:69] + "..."
    try:
        return template.format(summary=short or "what you shared", hint=hint)
    except (KeyError, ValueError):
        return template
