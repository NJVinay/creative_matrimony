"""
Content moderation — contact-sharing and abusive-language filters.
Applied to chat messages and to free-text profile fields, so members keep
conversations on the platform (women-first safety).
Trace: @context_documents/MVP_BACKLOG.md Epic G
"""

import re
import unicodedata
from functools import lru_cache

from app.config import settings

CONTACT_BLOCKED_MESSAGE = (
    "Message blocked: Sharing contact information (phone, email or social media handles) "
    "is not allowed. Please keep conversations on the platform."
)
ABUSE_BLOCKED_MESSAGE = (
    "Message blocked: Your message contains language that violates our community guidelines."
)

# ── Contact information ───────────────────────────────────

# Spelled-out digits (English, romanised Telugu and Hindi). People dictate
# numbers word by word to slip past digit filters.
_DIGIT_WORDS = {
    "0": ("zero", "oh", "sunna", "shunya", "shoonya"),
    "1": ("one", "okati", "okkati", "ek"),
    "2": ("two", "rendu", "do"),
    "3": ("three", "moodu", "mudu", "teen"),
    "4": ("four", "nalugu", "naalugu", "char", "chaar"),
    "5": ("five", "aidu", "ayidu", "paanch", "panch"),
    "6": ("six", "aaru", "chhe"),
    "7": ("seven", "edu", "eedu", "saat"),
    "8": ("eight", "enimidi", "enmidi", "aath"),
    "9": ("nine", "tommidi", "tommidhi", "nau"),
}
_DIGIT_WORD_MAP = {word: digit for digit, words in _DIGIT_WORDS.items() for word in words}
_DIGIT_WORD_RE = re.compile(r"\b(" + "|".join(_DIGIT_WORD_MAP) + r")\b")
_REPEAT_RE = re.compile(r"\b(double|triple)\s*(\d)")

# 10+ digits, optionally broken up by spaces, dashes, dots, brackets etc.
# ("98765 43210", "+91-98765-43210", "9 8 7 6 5 4 3 2 1 0"). Commas are not
# separators so Indian-format amounts ("10,00,000 - 15,00,000") stay allowed.
_PHONE_RE = re.compile(r"\d(?:[\s\-.()/\\_+*:|~]*\d){9,}")

# "name at gmail dot com", "name (at) gmail [dot] com", "name @ gmail.com"
_AT_RE = re.compile(r"\s*[(\[{<]\s*at\s*[)\]}>]\s*|\s+at\s+|\s*@\s*")
_DOT_RE = re.compile(r"\s*[(\[{<]\s*dot\s*[)\]}>]\s*|\s+dot\s+")
_EMAIL_RE = re.compile(r"[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}")
_EMAIL_PROVIDER_RE = re.compile(
    r"[a-z0-9._%+-]+@(?:gmail|googlemail|yahoo|ymail|hotmail|outlook|rediffmail|icloud|protonmail)\b"
)

# "@ravi_k" (an @ that does not belong to an email address)
_HANDLE_RE = re.compile(r"(?<![\w.@])@[a-z_][a-z0-9_.]{2,}")
# "insta: ravi_k", "fb id ravi.k", "telegram username is ravi"
_PLATFORMS = (
    r"(?:insta(?:gram)?|ig|telegram|snap(?:chat)?|facebook|fb|twitter|whats\s?app"
    r"|skype|linkedin)"
)
_PLATFORM_ID_RE = re.compile(
    rf"\b{_PLATFORMS}\s*(?:(?:id|handle|username|user\s*name)\b\s*(?:is\b|[:=\-])?|[:=])"
    r"\s*@?[a-z0-9_.]{3,}"
)


def _normalize_digits(text: str) -> str:
    """Lower-case, map Unicode digits (Telugu ౧, Devanagari १, fullwidth) and
    spelled-out digits to ASCII, and expand "double 9" / "triple 5"."""
    text = "".join(
        str(unicodedata.decimal(ch)) if ch.isdecimal() else ch for ch in text.casefold()
    )
    text = _DIGIT_WORD_RE.sub(lambda m: _DIGIT_WORD_MAP[m.group(1)], text)
    return _REPEAT_RE.sub(
        lambda m: m.group(2) * (2 if m.group(1) == "double" else 3), text
    )


def contains_contact_info(text: str | None) -> bool:
    """True if the text shares a phone number, email address or social handle."""
    if not text:
        return False
    lowered = text.casefold()
    if _PHONE_RE.search(_normalize_digits(text)):
        return True
    emailish = _DOT_RE.sub(".", _AT_RE.sub("@", lowered))
    if _EMAIL_RE.search(emailish) or _EMAIL_PROVIDER_RE.search(emailish):
        return True
    return bool(_HANDLE_RE.search(lowered) or _PLATFORM_ID_RE.search(lowered))


# ── Abusive language ──────────────────────────────────────

# Matched on whole words only, so "anti-harassment" or "Scunthorpe" pass.
# A trailing "*" also matches longer forms ("fuck*" → "fucking").
# Deliberately excludes words that are harmless in Telugu/Hindi chat, e.g.
# "randi" (Telugu: "please come") and "BC" (Backward Classes).
# Extend per deployment with MODERATION_BLOCKED_TERMS (comma-separated).
DEFAULT_BLOCKED_TERMS = (
    # English profanity, sexual harassment and threats
    "fuck*", "motherfuck*", "f*ck", "f**k", "bitch*", "bastard*", "slut*", "whore*",
    "cunt*", "asshole*", "dickhead*", "retard", "retarded", "nudes", "send nude*",
    "kill you", "rape you", "acid attack",
    # Hindi (romanised)
    "madarchod*", "maderchod*", "behenchod*", "bhenchod*", "chutiya*", "chutiye",
    "bhosdi*", "bhosad*", "bsdk", "harami", "haraami",
    # Telugu (romanised)
    "lanja", "lanjakodaka", "lanja kodaka", "dengu", "dengutha", "denginchuko",
    "modda", "puku", "kojja",
)


def _blocked_terms() -> tuple[str, ...]:
    extra = (t.strip().casefold() for t in settings.MODERATION_BLOCKED_TERMS.split(","))
    return DEFAULT_BLOCKED_TERMS + tuple(t for t in extra if t)


@lru_cache(maxsize=8)
def _abuse_pattern(terms: tuple[str, ...]) -> re.Pattern:
    parts = []
    for term in terms:
        wildcard = term.endswith("*")
        body = re.escape(term.rstrip("*") if wildcard else term).replace(r"\ ", r"\s+")
        parts.append(body + (r"\w*" if wildcard else ""))
    # (?<!\w)/(?!\w) rather than \b so terms containing "*" still anchor correctly
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)")


def contains_abuse(text: str | None) -> bool:
    """True if the text contains a blocked term (whole-word match)."""
    if not text:
        return False
    return bool(_abuse_pattern(_blocked_terms()).search(text.casefold()))


def check_chat_message(text: str) -> None:
    """Raise ValueError with a user-facing reason if a chat message is not allowed."""
    if contains_contact_info(text):
        raise ValueError(CONTACT_BLOCKED_MESSAGE)
    if contains_abuse(text):
        raise ValueError(ABUSE_BLOCKED_MESSAGE)
