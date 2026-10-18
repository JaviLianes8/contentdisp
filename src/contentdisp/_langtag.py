"""Well-formed language tags (RFC 5646 section 2.1), the language part of an ext-value."""

from __future__ import annotations

import re

# The Language-Tag ABNF of RFC 5646 section 2.1 written as one expression. ABNF quoted
# strings are case-insensitive and the singleton ranges list both cases, so the whole
# expression is matched without case; re.ASCII keeps non-ASCII letters (the Kelvin sign
# folds to "k") out of the letter classes.
_GRANDFATHERED = (
    "en-GB-oed|i-ami|i-bnn|i-default|i-enochian|i-hak|i-klingon|i-lux|i-mingo|i-navajo"
    "|i-pwn|i-tao|i-tay|i-tsu|sgn-BE-FR|sgn-BE-NL|sgn-CH-DE"
    "|art-lojban|cel-gaulish|no-bok|no-nyn|zh-guoyu|zh-hakka|zh-min|zh-min-nan|zh-xiang"
)
_PRIVATEUSE = r"x(?:-[a-z0-9]{1,8})+"
_LANGTAG = (
    r"(?:[a-z]{2,3}(?:-[a-z]{3}){0,3}|[a-z]{4}|[a-z]{5,8})"  # language, extlang
    r"(?:-[a-z]{4})?"  # script
    r"(?:-(?:[a-z]{2}|[0-9]{3}))?"  # region
    r"(?:-(?:[a-z0-9]{5,8}|[0-9][a-z0-9]{3}))*"  # variant
    r"(?:-[0-9a-wy-z](?:-[a-z0-9]{2,8})+)*"  # extension
    rf"(?:-{_PRIVATEUSE})?"
)
_LANGUAGE_TAG = re.compile(
    rf"(?:{_LANGTAG}|{_PRIVATEUSE}|{_GRANDFATHERED})", re.ASCII | re.IGNORECASE
)


def is_language_tag(text: str) -> bool:
    """True when ``text`` is a well-formed RFC 5646 Language-Tag."""
    return _LANGUAGE_TAG.fullmatch(text) is not None
