"""Keyword crisis stub and Singapore resource copy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# Risk level
RiskLevel = Literal["low", "elevated", "crisis"]

# Crisis patterns
CRISIS_PATTERNS = [
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bsuicid",
    r"\bself[-\s]?harm\b",
    r"\bwant to die\b",
    r"\bdon't want to (be )?alive\b",
    r"\bdont want to (be )?alive\b",
    r"\bhurt myself\b",
]

# Diagnosis patterns
DIAGNOSIS_PATTERNS = [
    r"\bdo i have (depression|anxiety|adhd|bipolar|ptsd)\b",
    r"\bam i (depressed|bipolar)\b",
    r"\bdiagnose me\b",
    r"\bwhat'?s wrong with me clinically\b",
]

# Medication patterns
MEDICATION_PATTERNS = [
    r"\b(double|increase|stop|skip) (my )?(dose|medication|meds|antidepressant)",
    r"\bshould i take\b.*\b(prozac|zoloft|xanax|antidepressant)",
    r"\bprescribe\b",
]

# Crisis message
CRISIS_MESSAGE = """
I'm really glad you shared that you're in a hard place. I'm not able to provide
crisis support or counselling here.

If you may be in danger right now, please contact emergency services: 995

Support lines in Singapore:
- Samaritans of Singapore (SOS): 1767
- IMH Helpline: 6389 2222

This app is peer-support infrastructure, not emergency care or therapy.
""".strip()

# Diagnosis refusal message
DIAGNOSIS_REFUSAL = """
I can't diagnose anyone or say whether you have a clinical condition.

I can help you reflect, connect with peer-support preferences in your circle,
or point to approved resources — without replacing a qualified professional.
""".strip()

# Medication refusal message
MEDICATION_REFUSAL = """
I can't give medication or treatment advice (including dose changes).

Please speak with a doctor or pharmacist about medicines. If this feels urgent,
use emergency services (995) or a crisis line (SOS 1767 / IMH 6389 2222).
""".strip()

# Safety result
@dataclass
class SafetyResult:
    level: RiskLevel
    category: str  # ok | crisis | diagnosis | medication
    message: str | None = None
    allow_facilitator_tools: bool = True

# Check if text matches any pattern
def _matches(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(re.search(p, lowered) for p in patterns)

# Assess message safety
def assess_message(text: str) -> SafetyResult:
    if _matches(text, CRISIS_PATTERNS):
        return SafetyResult(
            level="crisis",
            category="crisis",
            message=CRISIS_MESSAGE,
            allow_facilitator_tools=False,
        )
    if _matches(text, MEDICATION_PATTERNS):
        return SafetyResult(
            level="elevated",
            category="medication",
            message=MEDICATION_REFUSAL,
            allow_facilitator_tools=False,
        )
    if _matches(text, DIAGNOSIS_PATTERNS):
        return SafetyResult(
            level="elevated",
            category="diagnosis",
            message=DIAGNOSIS_REFUSAL,
            allow_facilitator_tools=False,
        )
    return SafetyResult(level="low", category="ok", allow_facilitator_tools=True)
