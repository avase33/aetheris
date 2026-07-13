"""PII detection & masking.

Scans text for common sensitive entities and replaces each with a stable,
reversible placeholder (``<EMAIL_1>`` …). Credit-card candidates are Luhn-checked
to cut false positives. The reverse map lets the proxy rehydrate placeholders in
an LLM response **locally**, so raw PII never leaves the network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..common.models import RedactionResult

# Ordered so higher-priority / more-specific patterns run first.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("API_KEY", re.compile(r"\b(?:sk|pk|ghp|xoxb|AKIA)[-_A-Za-z0-9]{12,}\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d[ \-]?){13,19}\b")),
    ("PHONE", re.compile(r"\b(?:\+?\d{1,2}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b")),
    ("IP", re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")),
]


def _luhn_ok(number: str) -> bool:
    digits = [int(c) for c in re.sub(r"\D", "", number)]
    if len(digits) < 13:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


@dataclass
class Redactor:
    mask_char_ip: bool = True
    _counts: dict[str, int] = field(default_factory=dict)

    def redact(self, text: str) -> tuple[RedactionResult, dict[str, str]]:
        """Return (result, reverse_map[placeholder -> original])."""
        counts: dict[str, int] = {}
        reverse: dict[str, str] = {}
        entities: list[dict] = []

        def make_placeholder(kind: str, original: str) -> str:
            counts[kind] = counts.get(kind, 0) + 1
            ph = f"<{kind}_{counts[kind]}>"
            reverse[ph] = original
            entities.append({"type": kind, "placeholder": ph})
            return ph

        for kind, pattern in PATTERNS:
            def repl(m: re.Match, _kind=kind) -> str:
                value = m.group(0)
                if _kind == "CREDIT_CARD" and not _luhn_ok(value):
                    return value  # not a valid card number; leave it
                return make_placeholder(_kind, value)

            text = pattern.sub(repl, text)

        return RedactionResult(redacted_text=text, entities=entities), reverse

    @staticmethod
    def rehydrate(text: str, reverse: dict[str, str]) -> str:
        for ph, original in reverse.items():
            text = text.replace(ph, original)
        return text
