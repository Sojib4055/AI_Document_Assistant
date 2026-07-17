from __future__ import annotations

import re


TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "according",
    "compare",
    "describe",
    "difference",
    "different",
    "explain",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "happen",
    "happens",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "me",
    "more",
    "my",
    "of",
    "on",
    "or",
    "please",
    "receive",
    "received",
    "receives",
    "receiving",
    "our",
    "same",
    "than",
    "tell",
    "the",
    "to",
    "under",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
    "would",
}
SYNONYMS = {
    "action": "act",
    "actions": "acts",
    "consider": "treat",
    "considered": "treated",
    "considering": "treating",
    "timing": "hours",
    "timings": "hours",
    "vacation": "leave",
    "holidays": "holiday",
    "illness": "sick",
    "medical": "sick",
    "jobs": "work",
    "job": "work",
    "terminate": "termination",
    "fired": "dismissal",
    "unused": "unavailed",
}
NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "fourteen": "14",
    "eighteen": "18",
    "thirty": "30",
    "forty": "40",
    "sixty": "60",
}


def tokenize(text: str, *, drop_stop_words: bool = True) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    output: list[str] = []
    for token in tokens:
        token = SYNONYMS.get(token, token)
        token = NUMBER_WORDS.get(token, token)
        if token.isdigit():
            token = str(int(token))
        if drop_stop_words and token in STOP_WORDS:
            continue
        output.append(token)
    return output
